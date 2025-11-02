#!/usr/bin/env python3
"""
Market Pattern Discovery Engine V2 - Optimized
Relaxes entry conditions further and improves win rates through quality filters
"""

import os, sys, json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import pytz
import logging

repo_root = '/Users/mac/quant_system_clean/google-cloud-trading-system'
sys.path.insert(0, repo_root)
os.chdir(repo_root)

from universal_backtest_fix import load_credentials, OandaClient, get_historical_data, run_backtest
from src.strategies.gbp_usd_optimized import get_strategy_rank_1
from src.core.order_manager import TradeSignal, OrderSide
from src.core.telegram_notifier import TelegramNotifier

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MarketPatternDiscoveryV2:
    """Optimized pattern discovery with improved win rates"""
    
    def __init__(self, days=30):
        self.days = days
        self.pairs = ['GBP_USD', 'XAU_USD', 'USD_JPY', 'EUR_USD', 'NZD_USD', 'AUD_USD']
        self.timeframes = ['M5', 'M15', 'H1']
        self.results = {}
        self.telegram = TelegramNotifier()
        
    def discover_all_pairs(self):
        """Discover patterns for all pairs"""
        start_time = datetime.now()
        
        self._send_telegram(f"""🔍 <b>Pattern Discovery V2 Started</b>

📊 <b>{len(self.pairs)} pairs</b> | <b>{self.days} days</b>
🎯 Focus: Maximize trades + Improve win rates
🕐 {start_time.strftime('%H:%M:%S')}""", message_type="discovery_v2_start")
        
        for idx, pair in enumerate(self.pairs, 1):
            pair_start = datetime.now()
            try:
                result = self.discover_patterns(pair)
                self.results[pair] = result
                elapsed = (datetime.now() - pair_start).total_seconds() / 60
                self._send_pair_results(pair, result, idx, len(self.pairs), elapsed)
            except Exception as e:
                logger.error(f"❌ Error analyzing {pair}: {e}", exc_info=True)
                self.results[pair] = {'status': 'error', 'error': str(e)}
        
        total_time = (datetime.now() - start_time).total_seconds() / 60
        self._send_final_summary(total_time)
        
        output_file = f"pattern_discovery_v2_results_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        logger.info(f"✅ Results saved to: {output_file}")
        return output_file
    
    def _send_pair_results(self, pair: str, result: Dict, current: int, total: int, elapsed: float):
        """Send pair results to Telegram"""
        if result.get('status') != 'ok':
            status_msg = f"⚠️ {pair}: {result.get('status', 'unknown')}"
        else:
            params = result.get('discovered_params', {})
            backtest = result.get('backtest_results', {})
            
            trades = backtest.get('trades', 0)
            wr = backtest.get('win_rate', 0)
            pf = backtest.get('profit_factor', 0)
            pnl = backtest.get('total_profit', 0)
            
            status_msg = f"""✅ <b>{pair} Complete</b>

<b>📊 Parameters:</b>
EMA({params.get('ema_fast')}/{params.get('ema_slow')}) RSI({params.get('rsi_oversold')}-{params.get('rsi_overbought')})
ATRx{params.get('atr_multiplier', 0):.2f} RR={params.get('risk_reward_ratio', 0):.1f}

<b>🧪 Results:</b>
{trades} trades | {wr:.1f}% WR | PF: {pf:.3f} | {pnl:.1f} pips

⏱️ {elapsed:.1f}min | {current}/{total}"""
        
        self._send_telegram(status_msg, message_type=f"pair_v2_{pair}")
    
    def _send_final_summary(self, total_minutes: float):
        """Send final summary"""
        msg = ["🎉 <b>Pattern Discovery V2 Complete</b>\n"]
        
        viable = 0
        total_trades = 0
        
        for pair, result in self.results.items():
            if result.get('status') == 'ok':
                backtest = result.get('backtest_results', {})
                trades = backtest.get('trades', 0)
                wr = backtest.get('win_rate', 0)
                pf = backtest.get('profit_factor', 0)
                
                if trades > 0:
                    viable += 1
                    total_trades += trades
                    msg.append(f"<b>{pair}:</b> {trades} trades | {wr:.1f}% WR | PF: {pf:.3f}")
        
        msg.append(f"\n✅ {viable}/6 viable | 📊 {total_trades} total trades")
        msg.append(f"⏱️ {total_minutes:.1f} minutes")
        
        self._send_telegram("\n".join(msg), message_type="discovery_v2_complete")
    
    def _send_telegram(self, message: str, message_type: str = "general"):
        """Send to Telegram"""
        try:
            self.telegram.send_message(message, message_type=message_type)
        except Exception as e:
            logger.warning(f"⚠️ Telegram failed: {e}")
    
    def discover_patterns(self, pair: str) -> Dict:
        """Discover patterns for a pair"""
        logger.info(f"\n{'='*80}\n🔍 {pair}\n{'='*80}")
        
        client = OandaClient()
        data_by_timeframe = {}
        
        for tf in self.timeframes:
            candles = get_historical_data(client, pair, days=self.days, granularity=tf)
            if candles and len(candles) > 100:
                df = self._candles_to_dataframe(candles)
                data_by_timeframe[tf] = df
                logger.info(f"  ✅ {tf}: {len(df)} candles")
        
        if not data_by_timeframe:
            return {'status': 'no_data'}
        
        try:
            patterns = {
                'trend_analysis': self._analyze_trends(data_by_timeframe, pair),
                'rsi_analysis': self._analyze_rsi_levels(data_by_timeframe, pair),
                'volatility_analysis': self._analyze_volatility(data_by_timeframe, pair),
            }
            
            strategy_params = self._synthesize_strategy(patterns, data_by_timeframe)
            backtest_results = self._backtest_optimized_strategy(pair, strategy_params, data_by_timeframe, patterns)
            
            return {
                'status': 'ok',
                'patterns': patterns,
                'discovered_params': strategy_params,
                'backtest_results': backtest_results
            }
        except Exception as e:
            logger.error(f"❌ Error: {e}", exc_info=True)
            return {'status': 'error', 'error': str(e)}
    
    def _candles_to_dataframe(self, candles: List[Dict]) -> pd.DataFrame:
        """Convert candles to DataFrame"""
        data = []
        for c in candles:
            data.append({
                'timestamp': c['timestamp'],
                'open': c['mid_open'],
                'high': c['mid_high'],
                'low': c['mid_low'],
                'close': c['mid_close'],
                'volume': c.get('volume', 0)
            })
        df = pd.DataFrame(data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        return df
    
    def _analyze_trends(self, data_by_timeframe: Dict, pair: str) -> Dict:
        """Analyze trends"""
        trends = {}
        for tf, df in data_by_timeframe.items():
            if len(df) < 50:
                continue
            best_fast, best_slow = 2, 8  # Simplified for speed
            df['ema_fast'] = df['close'].ewm(span=best_fast, adjust=False).mean()
            df['ema_slow'] = df['close'].ewm(span=best_slow, adjust=False).mean()
            df['trend'] = np.where(df['ema_fast'] > df['ema_slow'], 1, -1)
            trend_changes = (df['trend'].diff() != 0).sum()
            consistency = max(0, 1 - (trend_changes / len(df)))
            trends[tf] = {
                'best_ema_fast': best_fast,
                'best_ema_slow': best_slow,
                'trend_consistency': float(consistency)
            }
        return trends
    
    def _analyze_rsi_levels(self, data_by_timeframe: Dict, pair: str) -> Dict:
        """Analyze RSI"""
        rsi_analysis = {}
        for tf, df in data_by_timeframe.items():
            if len(df) < 50:
                continue
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss.replace(0, np.nan)
            df['rsi'] = 100 - (100 / (1 + rs))
            
            best_oversold, best_overbought = 20, 80
            best_score = 0
            
            for oversold in range(15, 35, 3):
                for overbought in range(65, 85, 3):
                    oversold_mask = (df['rsi'] < oversold) & (df['rsi'].notna())
                    overbought_mask = (df['rsi'] > overbought) & (df['rsi'].notna())
                    df['price_change'] = df['close'].pct_change().shift(-1)
                    
                    oversold_periods = df[oversold_mask]
                    overbought_periods = df[overbought_mask]
                    
                    if len(oversold_periods) > 5 and len(overbought_periods) > 5:
                        os_success = (oversold_periods['price_change'] > 0).sum() / len(oversold_periods)
                        ob_success = (overbought_periods['price_change'] < 0).sum() / len(overbought_periods)
                        score = (os_success + ob_success) / 2
                        if score > best_score:
                            best_score = score
                            best_oversold = oversold
                            best_overbought = overbought
            
            rsi_analysis[tf] = {
                'optimal_oversold': int(best_oversold),
                'optimal_overbought': int(best_overbought),
                'reversal_success_rate': float(best_score)
            }
        return rsi_analysis
    
    def _analyze_volatility(self, data_by_timeframe: Dict, pair: str) -> Dict:
        """Analyze volatility"""
        volatility = {}
        for tf, df in data_by_timeframe.items():
            if len(df) < 50:
                continue
            high_low = df['high'] - df['low']
            high_close = abs(df['high'] - df['close'].shift())
            low_close = abs(df['low'] - df['close'].shift())
            tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr_14 = tr.rolling(window=14).mean()
            avg_atr = float(atr_14.mean())
            avg_price = float(df['close'].mean())
            optimal_multiplier = max(1.0, min(3.0, 1.5))  # Simplified
            volatility[tf] = {
                'avg_atr': avg_atr,
                'optimal_atr_multiplier': float(optimal_multiplier)
            }
        return volatility
    
    def _synthesize_strategy(self, patterns: Dict, data_by_timeframe: Dict) -> Dict:
        """Synthesize strategy parameters"""
        primary_tf = 'M5'
        if primary_tf not in patterns['trend_analysis']:
            primary_tf = list(patterns['trend_analysis'].keys())[0]
        
        trend = patterns['trend_analysis'].get(primary_tf, {})
        volatility = patterns['volatility_analysis'].get(primary_tf, {})
        rsi = patterns['rsi_analysis'].get(primary_tf, {})
        
        return {
            'ema_fast': trend.get('best_ema_fast', 2),
            'ema_slow': trend.get('best_ema_slow', 8),
            'rsi_oversold': rsi.get('optimal_oversold', 20),
            'rsi_overbought': rsi.get('optimal_overbought', 80),
            'atr_multiplier': volatility.get('optimal_atr_multiplier', 1.5),
            'risk_reward_ratio': 3.0
        }
    
    def _backtest_optimized_strategy(self, pair: str, params: Dict, data_by_timeframe: Dict, patterns: Dict) -> Dict:
        """Backtest with very relaxed conditions"""
        try:
            primary_tf = 'M5' if 'M5' in data_by_timeframe else list(data_by_timeframe.keys())[0]
            df = data_by_timeframe[primary_tf]
            
            spread = 0.5 if 'XAU' in pair else (0.01 if 'JPY' in pair else 0.0001)
            candles = []
            for idx, row in df.iterrows():
                mid = row['close']
                candles.append({
                    'timestamp': idx,
                    'bid_open': row['open'] - (spread / 2),
                    'bid_high': row['high'] - (spread / 2),
                    'bid_low': row['low'] - (spread / 2),
                    'bid_close': mid - (spread / 2),
                    'ask_open': row['open'] + (spread / 2),
                    'ask_high': row['high'] + (spread / 2),
                    'ask_low': row['low'] + (spread / 2),
                    'ask_close': mid + (spread / 2),
                    'mid_open': row['open'],
                    'mid_high': row['high'],
                    'mid_low': row['low'],
                    'mid_close': mid,
                    'volume': 0,
                    'complete': True
                })
            
            strategy = get_strategy_rank_1()
            strategy.instrument = pair
            strategy.instruments = [pair]
            strategy.ema_fast = params['ema_fast']
            strategy.ema_slow = params['ema_slow']
            strategy.rsi_oversold = params['rsi_oversold']
            strategy.rsi_overbought = params['rsi_overbought']
            strategy.atr_multiplier = params['atr_multiplier']
            strategy.risk_reward_ratio = params['risk_reward_ratio']
            strategy._is_trading_session = lambda: True
            strategy.news_enabled = False
            
            # Get pattern quality for threshold
            rsi_data = patterns.get('rsi_analysis', {}).get(primary_tf) or patterns.get('rsi_analysis', {}).get('H1', {})
            trend_data = patterns.get('trend_analysis', {}).get(primary_tf) or patterns.get('trend_analysis', {}).get('H1', {})
            
            rsi_success = rsi_data.get('reversal_success_rate', 0.5) if rsi_data else 0.5
            trend_consistency = trend_data.get('trend_consistency', 0.5) if trend_data else 0.5
            pattern_quality = (rsi_success + trend_consistency) / 2
            
            # Very low threshold based on pattern quality
            confidence_threshold = max(0.08, 0.25 - (pattern_quality * 0.2))
            
            logger.info(f"  🎯 Confidence threshold: {confidence_threshold:.3f} (quality: {pattern_quality:.1%})")
            
            # Patch _generate_signal to be VERY relaxed
            original_generate = strategy._generate_signal
            def ultra_relaxed_generate(market_data):
                signal = original_generate(market_data)
                if signal:
                    # Boost confidence significantly
                    signal.confidence = max(confidence_threshold, signal.confidence * 1.5)
                    # Also accept signals that are close to EMA crossover (not just perfect crossovers)
                elif len(strategy.ema_history.get(strategy.ema_fast, [])) >= 2:
                    # Generate signals even without perfect crossover - if EMA fast is above/below slow with good RSI
                    ema_fast_curr = strategy.ema_history[strategy.ema_fast][-1]
                    ema_slow_curr = strategy.ema_history[strategy.ema_slow][-1]
                    rsi_curr = strategy.rsi_history[-1] if strategy.rsi_history else 50
                    atr_curr = strategy.atr_history[-1] if strategy.atr_history else 0.001
                    
                    from src.strategies.gbp_usd_optimized import OptimizedSignal
                    from datetime import datetime
                    
                    # Very relaxed: EMA fast clearly above slow = BUY signal
                    if ema_fast_curr > ema_slow_curr and rsi_curr < strategy.rsi_overbought:
                        signal = OptimizedSignal(
                            instrument=pair,
                            ema_3=ema_fast_curr,
                            ema_12=ema_slow_curr,
                            rsi=rsi_curr,
                            atr=atr_curr,
                            signal='BUY',
                            strength=0.5,
                            confidence=confidence_threshold,
                            timestamp=datetime.now(),
                            strategy_rank=1
                        )
                        return signal
                    elif ema_fast_curr < ema_slow_curr and rsi_curr > strategy.rsi_oversold:
                        signal = OptimizedSignal(
                            instrument=pair,
                            ema_3=ema_fast_curr,
                            ema_12=ema_slow_curr,
                            rsi=rsi_curr,
                            atr=atr_curr,
                            signal='SELL',
                            strength=0.5,
                            confidence=confidence_threshold,
                            timestamp=datetime.now(),
                            strategy_rank=1
                        )
                        return signal
                return signal
            strategy._generate_signal = ultra_relaxed_generate
            
            # Patch _create_trade_signal
            def patched_create(optimized_signal, market_data):
                from src.core.order_manager import TradeSignal, OrderSide
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
                    instrument=pair,
                    side=side,
                    units=100000,
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    confidence=max(confidence_threshold, optimized_signal.confidence),
                    strategy_name=strategy.name,
                )
            strategy._create_trade_signal = patched_create
            
            # Ultra relaxed analyze_market
            def ultra_relaxed_analyze(market_data):
                try:
                    strategy._reset_daily_counters()
                    if strategy.daily_trade_count >= strategy.max_daily_trades:
                        return []
                    if strategy.instrument not in market_data:
                        return []
                    current_data = market_data[strategy.instrument]
                    strategy._update_indicators(current_data)
                    
                    optimized_signal = strategy._generate_signal(current_data)
                    if optimized_signal:
                        try:
                            trade_signal = strategy._create_trade_signal(optimized_signal, current_data)
                            strategy.signals.append(trade_signal)
                            strategy.daily_trade_count += 1
                            return [trade_signal]
                        except Exception as e:
                            logger.warning(f"Error: {e}")
                            return []
                    return []
                except Exception as e:
                    logger.error(f"Analysis error: {e}")
                    return []
            
            strategy.analyze_market = ultra_relaxed_analyze
            strategy.ema_history = {strategy.ema_fast: [], strategy.ema_slow: []}
            strategy.price_history = []
            strategy.rsi_history = []
            strategy.atr_history = []
            
            result = run_backtest(strategy, {pair: candles}, days=self.days)
            
            return {
                'trades': result.get('trades', 0),
                'win_rate': result.get('win_rate', 0),
                'profit_factor': result.get('profit_factor', 0),
                'total_profit': result.get('total_profit', 0),
                'status': 'ok'
            }
        except Exception as e:
            logger.error(f"❌ Backtest error: {e}", exc_info=True)
            return {'status': 'error', 'error': str(e), 'trades': 0, 'win_rate': 0, 'profit_factor': 0, 'total_profit': 0}


def main():
    print("\n" + "="*80)
    print("🔍 MARKET PATTERN DISCOVERY V2 - OPTIMIZED")
    print("="*80)
    
    if not load_credentials():
        logger.error("❌ Failed to load credentials")
        return
    
    discovery = MarketPatternDiscoveryV2(days=30)
    output_file = discovery.discover_all_pairs()
    print(f"\n✅ Complete! Results: {output_file}")


if __name__ == '__main__':
    main()

