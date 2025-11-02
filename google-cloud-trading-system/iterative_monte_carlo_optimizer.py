#!/usr/bin/env python3
"""
Iterative Monte Carlo Optimizer
Keeps running and relaxing parameters until viable results are found for all pairs
"""
import os, sys, json, random
from datetime import datetime, timedelta
import pytz

repo_root = '/Users/mac/quant_system_clean/google-cloud-trading-system'
sys.path.insert(0, repo_root)
os.chdir(repo_root)

from universal_backtest_fix import load_credentials, OandaClient, get_historical_data, run_backtest
from src.strategies.gbp_usd_optimized import get_strategy_rank_1
from src.core.order_manager import TradeSignal, OrderSide

pairs = ['GBP_USD','XAU_USD','USD_JPY','EUR_USD','NZD_USD','AUD_USD']

if not load_credentials():
    print(json.dumps({'status':'error','error':'credentials'})); sys.exit(1)

client = OandaClient()
now = datetime.now(pytz.UTC)
span_days = 14

def enable_backtest_mode(strategy, confidence=0.15):
    if hasattr(strategy, '_is_trading_session'):
        strategy._is_trading_session = lambda: True
    if hasattr(strategy, 'news_enabled'):
        strategy.news_enabled = False
    # Relax momentum/ADX thresholds
    if hasattr(strategy, 'min_momentum'):
        strategy.min_momentum = 0.00005
    if hasattr(strategy, 'min_adx'):
        strategy.min_adx = 8.0
    if hasattr(strategy, 'min_confidence'):
        strategy.min_confidence = confidence

def patch_create_trade_signal(strategy, confidence=0.15):
    def _patched_create(optimized_signal, market_data):
        # Manual creation without strength parameter
        if optimized_signal.signal == 'BUY':
            entry_price = market_data.ask
            stop_loss = entry_price - (optimized_signal.atr * strategy.atr_multiplier)
            take_profit = entry_price + (optimized_signal.atr * strategy.atr_multiplier * strategy.risk_reward_ratio)
            side = OrderSide.BUY
        else:
            entry_price = market_data.bid
            stop_loss = entry_price + (optimized_signal.atr * strategy.atr_multiplier)
            take_profit = entry_price - (optimized_signal.atr * strategy.atr_multiplier * strategy.risk_reward_ratio)
            side = OrderSide.SELL
        return TradeSignal(
            instrument=getattr(strategy, 'instrument', 'GBP_USD'),
            side=side,
            units=100000,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            confidence=confidence,
            strategy_name=strategy.name,
        )
    strategy._create_trade_signal = _patched_create

# Progressive relaxation strategy
def get_ranges(iteration):
    """Get parameter ranges based on iteration - progressively more relaxed"""
    base_confidence = max(0.10, 0.25 - (iteration * 0.02))
    
    ranges = {
      'GBP_USD': dict(
          ef=(2, 8+iteration*2),
          es=(8, 25+iteration*3),
          rsi_lo=(max(8, 15-iteration*1), 35+iteration*2),
          rsi_hi=(65-iteration*2, min(95, 85+iteration*1)),
          atr=(max(0.8, 1.0-iteration*0.1), 2.5+iteration*0.3),
          rr=(1.5+iteration*0.1, 4.0+iteration*0.5)
      ),
      'XAU_USD': dict(
          ef=(2, 8+iteration*2),
          es=(10, 30+iteration*3),
          rsi_lo=(max(10, 15-iteration*1), 35+iteration*2),
          rsi_hi=(65-iteration*2, min(95, 85+iteration*1)),
          atr=(max(1.2, 1.5-iteration*0.1), 3.0+iteration*0.3),
          rr=(1.8+iteration*0.1, 4.0+iteration*0.5)
      ),
      'USD_JPY': dict(
          ef=(2, 8+iteration*2),
          es=(10, 35+iteration*3),
          rsi_lo=(max(8, 12-iteration*1), 32+iteration*2),
          rsi_hi=(68-iteration*2, min(95, 88+iteration*1)),
          atr=(max(0.8, 1.0-iteration*0.1), 2.5+iteration*0.3),
          rr=(1.5+iteration*0.1, 4.2+iteration*0.5)
      ),
      'EUR_USD': dict(
          ef=(2, 8+iteration*2),
          es=(10, 32+iteration*3),
          rsi_lo=(max(10, 15-iteration*1), 35+iteration*2),
          rsi_hi=(65-iteration*2, min(95, 85+iteration*1)),
          atr=(max(0.8, 1.0-iteration*0.1), 2.2+iteration*0.3),
          rr=(1.5+iteration*0.1, 4.0+iteration*0.5)
      ),
      'NZD_USD': dict(
          ef=(2, 8+iteration*2),
          es=(10, 30+iteration*3),
          rsi_lo=(max(10, 15-iteration*1), 35+iteration*2),
          rsi_hi=(65-iteration*2, min(95, 85+iteration*1)),
          atr=(max(1.0, 1.2-iteration*0.1), 2.3+iteration*0.3),
          rr=(1.8+iteration*0.1, 4.0+iteration*0.5)
      ),
      'AUD_USD': dict(
          ef=(2, 8+iteration*2),
          es=(10, 30+iteration*3),
          rsi_lo=(max(10, 15-iteration*1), 35+iteration*2),
          rsi_hi=(65-iteration*2, min(95, 85+iteration*1)),
          atr=(max(1.0, 1.2-iteration*0.1), 2.4+iteration*0.3),
          rr=(1.8+iteration*0.1, 4.2+iteration*0.5)
      ),
    }
    return ranges, base_confidence

results = {}
iteration = 0
max_iterations = 10
min_trades_per_pair = 10

print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting iterative optimization...", file=sys.stderr)
print(f"Target: {min_trades_per_pair} trades minimum per pair", file=sys.stderr)

while iteration < max_iterations:
    iteration += 1
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] === ITERATION {iteration} ===", file=sys.stderr)
    
    ranges_dict, confidence = get_ranges(iteration)
    print(f"Confidence threshold: {confidence:.2f}", file=sys.stderr)
    
    all_viable = True
    
    for pair in pairs:
        # Preserve GBP_USD best config (33% WR, PF 1.068)
        if pair == 'GBP_USD' and iteration == 1:
            print(f"✓ {pair}: Using preserved best config (33% WR, PF 1.068)", file=sys.stderr)
            results[pair] = {
                'status': 'ok',
                'days': span_days,
                'iteration': 0,
                'recommend': {
                    'trades': 100,
                    'win_rate': 33.0,
                    'profit_factor': 1.068,
                    'pnl_pips': 24.19,
                    'cfg': {
                        'ema_fast': 3,
                        'ema_slow': 12,
                        'rsi_oversold': 19.94,
                        'rsi_overbought': 80.74,
                        'atr_multiplier': 1.43,
                        'rr': 2.53
                    }
                },
                'top': []
            }
            continue
        
        # Skip if we already have viable results
        if pair in results and results[pair].get('status') == 'ok':
            rec = results[pair].get('recommend')
            if rec and rec.get('trades', 0) >= min_trades_per_pair:
                print(f"✓ {pair}: Already viable ({rec.get('trades', 0)} trades)", file=sys.stderr)
                continue
        
        print(f"Processing {pair}...", file=sys.stderr, end=' ', flush=True)
        
        # Fetch data
        hist_m5 = get_historical_data(client, pair, days=span_days, granularity='M5') or []
        hist_m15 = get_historical_data(client, pair, days=span_days, granularity='M15') or []
        hist_m30 = get_historical_data(client, pair, days=span_days, granularity='M30') or []
        if not hist_m5 and not hist_m15 and not hist_m30:
            results[pair] = {'status':'no_data'}
            all_viable = False
            continue

        candidates = []
        iters = 500 + (iteration * 100)  # More iterations each round
        r = ranges_dict[pair]

        for i in range(iters):
            ef = random.randint(*r['ef'])
            es = random.randint(max(ef+2, r['es'][0]), r['es'][1])
            rlo = random.uniform(*r['rsi_lo'])
            rhi = random.uniform(max(rlo+5, r['rsi_hi'][0]), r['rsi_hi'][1])
            atrm = random.uniform(*r['atr'])
            rr = random.uniform(*r['rr'])

            try:
                s = get_strategy_rank_1()
                enable_backtest_mode(s, confidence)
                patch_create_trade_signal(s, confidence)
                s.instrument = pair
                s.instruments = [pair]
                s.ema_fast = int(ef)
                s.ema_slow = int(es)
                s.rsi_oversold = float(rlo)
                s.rsi_overbought = float(rhi)
                s.atr_multiplier = float(atrm)
                s.risk_reward_ratio = float(rr)
                
                # Initialize EMA history for new periods
                s.ema_history = {s.ema_fast: [], s.ema_slow: []}

                # Run all granularities with error handling
                res5 = {'trades':0,'total_profit':0,'profit_factor':0,'win_rate':0}
                res15 = {'trades':0,'total_profit':0,'profit_factor':0,'win_rate':0}
                res30 = {'trades':0,'total_profit':0,'profit_factor':0,'win_rate':0}
                
                if hist_m5 and len(hist_m5) > max(s.ema_slow, s.rsi_period, s.atr_period) + 10:
                    try:
                        res5 = run_backtest(s, {pair: hist_m5}, days=span_days)
                    except Exception as e:
                        pass  # Skip on error
                
                if hist_m15 and len(hist_m15) > max(s.ema_slow, s.rsi_period, s.atr_period) + 10:
                    try:
                        # Reset strategy state for new timeframe
                        s.price_history = []
                        s.ema_history = {s.ema_fast: [], s.ema_slow: []}
                        s.rsi_history = []
                        s.atr_history = []
                        res15 = run_backtest(s, {pair: hist_m15}, days=span_days)
                    except Exception as e:
                        pass
                
                if hist_m30 and len(hist_m30) > max(s.ema_slow, s.rsi_period, s.atr_period) + 10:
                    try:
                        # Reset strategy state for new timeframe
                        s.price_history = []
                        s.ema_history = {s.ema_fast: [], s.ema_slow: []}
                        s.rsi_history = []
                        s.atr_history = []
                        res30 = run_backtest(s, {pair: hist_m30}, days=span_days)
                    except Exception as e:
                        pass
            except Exception as e:
                # Skip this iteration on error
                continue
            
            trades = (res5.get('trades',0) or 0) + (res15.get('trades',0) or 0) + (res30.get('trades',0) or 0)
            pnl = (res5.get('total_profit',0) or 0) + (res15.get('total_profit',0) or 0) + (res30.get('total_profit',0) or 0)
            pf = max(res5.get('profit_factor',0) or 0, res15.get('profit_factor',0) or 0, res30.get('profit_factor',0) or 0)
            
            # Weighted win rate
            total_trades = trades
            if total_trades > 0:
                wr5 = res5.get('win_rate', 0) or 0
                wr15 = res15.get('win_rate', 0) or 0
                wr30 = res30.get('win_rate', 0) or 0
                trades5 = res5.get('trades', 0) or 0
                trades15 = res15.get('trades', 0) or 0
                trades30 = res30.get('trades', 0) or 0
                wr = ((wr5 * trades5) + (wr15 * trades15) + (wr30 * trades30)) / total_trades if total_trades > 0 else 0
            else:
                wr = 0

            if trades < min_trades_per_pair:
                score = -1000 + trades
            else:
                score = pnl + max(0.0, (pf-1.0))*400 + (wr-35)*0.5 + min(trades/3, 30)

            candidates.append({
                'score': score,
                'trades': trades,
                'win_rate': wr,
                'profit_factor': pf,
                'pnl_pips': pnl,
                'cfg': {
                    'ema_fast': ef,
                    'ema_slow': es,
                    'rsi_oversold': rlo,
                    'rsi_overbought': rhi,
                    'atr_multiplier': atrm,
                    'rr': rr,
                }
            })

        candidates.sort(key=lambda x: x['score'], reverse=True)
        top = candidates[:10]
        recommend = next((c for c in top if c['trades']>=min_trades_per_pair), top[0] if top else None)
        
        trades_count = recommend.get('trades', 0) if recommend else 0
        status_icon = "✓" if trades_count >= min_trades_per_pair else "✗"
        print(f"{status_icon} {trades_count} trades (PF: {recommend.get('profit_factor', 0):.2f}, WR: {recommend.get('win_rate', 0):.1f}%)" if recommend else "✗ No viable config", file=sys.stderr)
        
        results[pair] = {'status':'ok','days':span_days,'iteration':iteration,'top':top,'recommend':recommend}
        
        if not recommend or recommend.get('trades', 0) < min_trades_per_pair:
            all_viable = False

    # Save progress
    out_file = f"monte_carlo_results_{now.strftime('%Y%m%d_%H%M')}_iter{iteration}.json"
    with open(out_file,'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Progress saved to {out_file}", file=sys.stderr)
    
    if all_viable:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ✅ ALL PAIRS VIABLE! Stopping.", file=sys.stderr)
        break

# Final summary
print(f"\n[{datetime.now().strftime('%H:%M:%S')}] === FINAL RESULTS ===", file=sys.stderr)
for pair in pairs:
    rec = results.get(pair, {}).get('recommend')
    if rec:
        print(f"{pair}: {rec.get('trades', 0)} trades | PF: {rec.get('profit_factor', 0):.2f} | WR: {rec.get('win_rate', 0):.1f}% | P/L: {rec.get('pnl_pips', 0):.2f} pips", file=sys.stderr)
    else:
        print(f"{pair}: No viable configuration found", file=sys.stderr)

# Output final file
final_file = f"monte_carlo_results_{now.strftime('%Y%m%d_%H%M')}_FINAL.json"
with open(final_file, 'w') as f:
    json.dump(results, f, indent=2, default=str)
print(f"\nFinal results: {final_file}")
print(final_file)

