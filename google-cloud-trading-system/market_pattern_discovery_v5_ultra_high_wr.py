#!/usr/bin/env python3
"""
Market Pattern Discovery V5 - Ultra High Win Rate Target (60%+)
Extremely selective with multiple confirmations - only best setups
"""

import os, sys, json
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
import pytz
import logging

repo_root = '/Users/mac/quant_system_clean/google-cloud-trading-system'
sys.path.insert(0, repo_root)
os.chdir(repo_root)

from universal_backtest_fix import load_credentials, OandaClient, get_historical_data
from src.core.telegram_notifier import TelegramNotifier

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MarketPatternDiscoveryV5:
    """V5: Ultra-high win rate target (60%+) - extremely selective"""
    
    def __init__(self, days=30):
        self.days = days
        self.pairs = ['GBP_USD', 'XAU_USD', 'USD_JPY', 'EUR_USD', 'NZD_USD', 'AUD_USD']
        self.timeframes = ['M5', 'M15', 'H1']
        self.results = {}
        self.telegram = TelegramNotifier()
        
    def discover_all_pairs(self):
        """Discover and optimize for 60%+ win rate"""
        start_time = datetime.now()
        self._send_telegram(f"""🎯 <b>Pattern Discovery V5 - 60%+ WR Target</b>

📊 <b>{len(self.pairs)} pairs</b> | <b>{self.days} days</b>
🔥 ULTRA-SELECTIVE: Multiple confirmations required
⭐ Target: 60%+ Win Rate
🕐 {start_time.strftime('%H:%M:%S')}""", message_type="v5_start")
        
        for idx, pair in enumerate(self.pairs, 1):
            pair_start = datetime.now()
            try:
                result = self.optimize_for_high_wr(pair)
                self.results[pair] = result
                elapsed = (datetime.now() - pair_start).total_seconds() / 60
                self._send_pair_results(pair, result, idx, len(self.pairs), elapsed)
            except Exception as e:
                logger.error(f"❌ Error optimizing {pair}: {e}", exc_info=True)
                self.results[pair] = {'status': 'error', 'error': str(e)}
        
        total_time = (datetime.now() - start_time).total_seconds() / 60
        self._send_final_summary(total_time)
        
        output_file = f"pattern_discovery_v5_results_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        logger.info(f"✅ Results saved to: {output_file}")
        return output_file
    
    def _send_pair_results(self, pair: str, result: Dict, current: int, total: int, elapsed: float):
        """Send pair results to Telegram"""
        if result.get('status') != 'ok':
            status_msg = f"⚠️ {pair}: {result.get('status', 'unknown')}"
        else:
            best_config = result.get('best_config', {})
            backtest = result.get('backtest_results', {})
            
            trades = backtest.get('trades', 0)
            wr = backtest.get('win_rate', 0)
            pf = backtest.get('profit_factor', 0)
            pnl = backtest.get('total_profit', 0)
            
            filters = best_config.get('filters', {})
            
            status_icon = "🎯" if wr >= 60 else ("✅" if wr >= 50 else ("⚠️" if trades > 0 else "❌"))
            
            status_msg = f"""{status_icon} <b>{pair}</b> {wr:.1f}% WR

<b>📊 Config:</b>
EMA({best_config.get('ema_fast')}/{best_config.get('ema_slow')}) RSI({best_config.get('rsi_oversold')}-{best_config.get('rsi_overbought')})
ATRx{best_config.get('atr_multiplier', 0):.2f} RR={best_config.get('risk_reward_ratio', 0):.1f}

<b>🔥 Ultra Filters:</b>
RSI Extreme: {filters.get('rsi_extreme', 0):.0f} | EMA Sep: {filters.get('min_ema_separation', 0):.5f}
Momentum: {filters.get('min_momentum', 0):.5f} | Trend Strength: {filters.get('trend_strength', 0):.3f}
Volatility: {filters.get('volatility_filter', False)}

<b>🧪 Results:</b>
{trades} trades | {wr:.1f}% WR | PF: {pf:.3f} | {pnl:.1f} pips

⏱️ {elapsed:.1f}min | {current}/{total}"""
        
        self._send_telegram(status_msg, message_type=f"pair_v5_{pair}")
    
    def _send_final_summary(self, total_minutes: float):
        """Send final summary"""
        msg = ["🎯 <b>Pattern Discovery V5 Complete</b>\n"]
        
        viable = 0
        total_trades = 0
        high_wr = []
        ultra_high = []
        
        for pair, result in self.results.items():
            if result.get('status') == 'ok':
                backtest = result.get('backtest_results', {})
                trades = backtest.get('trades', 0)
                wr = backtest.get('win_rate', 0)
                pf = backtest.get('profit_factor', 0)
                
                if trades > 0:
                    viable += 1
                    total_trades += trades
                    if wr >= 60:
                        ultra_high.append(f"{pair}: {wr:.1f}%")
                    elif wr >= 50:
                        high_wr.append(f"{pair}: {wr:.1f}%")
                    msg.append(f"<b>{pair}:</b> {trades} trades | {wr:.1f}% WR | PF: {pf:.3f}")
        
        msg.append(f"\n✅ {viable}/6 viable | 📊 {total_trades} total trades")
        if ultra_high:
            msg.append(f"🔥 60%+ WR: {', '.join(ultra_high)}")
        if high_wr:
            msg.append(f"⭐ 50%+ WR: {', '.join(high_wr)}")
        msg.append(f"⏱️ {total_minutes:.1f} minutes")
        
        self._send_telegram("\n".join(msg), message_type="v5_complete")
    
    def _send_telegram(self, message: str, message_type: str = "general"):
        """Send to Telegram"""
        try:
            self.telegram.send_message(message, message_type=message_type)
        except Exception as e:
            logger.warning(f"⚠️ Telegram failed: {e}")
    
    def optimize_for_high_wr(self, pair: str) -> Dict:
        """Optimize for 60%+ win rate with ultra-selective filters"""
        logger.info(f"\n{'='*80}\n🎯 Optimizing {pair} for 60%+ WR\n{'='*80}")
        
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
            
            primary_tf = 'M5' if 'M5' in data_by_timeframe else list(data_by_timeframe.keys())[0]
            df = data_by_timeframe[primary_tf]
            base_params = self._synthesize_strategy(patterns, data_by_timeframe)
            
            # EXTREMELY STRICT FILTER COMBINATIONS
            best_config = None
            best_score = -999999
            best_backtest = None
            
            # Test many combinations - be VERY selective
            for rsi_extreme in [10, 15, 20, 25]:  # How extreme RSI must be
                for min_ema_sep in [0.0003, 0.0005, 0.0007, 0.001, 0.0015]:  # Strong trend requirement
                    for min_momentum in [0.0002, 0.0003, 0.0005, 0.0007]:  # Strong momentum
                        for trend_strength in [0.7, 0.75, 0.8, 0.85]:  # Trend consistency
                            for use_volatility_filter in [True, False]:
                                config = {
                                    'ema_fast': base_params['ema_fast'],
                                    'ema_slow': base_params['ema_slow'],
                                    'rsi_oversold': max(10, base_params['rsi_oversold'] - rsi_extreme),
                                    'rsi_overbought': min(90, base_params['rsi_overbought'] + rsi_extreme),
                                    'atr_multiplier': base_params['atr_multiplier'],
                                    'risk_reward_ratio': 3.0,
                                    'filters': {
                                        'rsi_extreme': rsi_extreme,
                                        'min_ema_separation': min_ema_sep,
                                        'min_momentum': min_momentum,
                                        'trend_strength': trend_strength,
                                        'volatility_filter': use_volatility_filter
                                    }
                                }
                                
                                backtest_result = self._backtest_ultra_selective(pair, config, df.copy())
                                
                                # Prioritize win rate - need at least 15 trades and 55%+ WR to consider
                                if backtest_result['trades'] >= 15 and backtest_result['win_rate'] >= 55:
                                    score = (
                                        backtest_result['win_rate'] * 200 +  # Heavily weight win rate
                                        (backtest_result['profit_factor'] - 1.0) * 300 +  # PF weight
                                        min(backtest_result['trades'] / 3, 40) -  # Trade count (capped)
                                        (abs(backtest_result['total_profit']) / 50 if backtest_result['total_profit'] < 0 else 0)
                                    )
                                    
                                    if score > best_score:
                                        best_score = score
                                        best_config = config
                                        best_backtest = backtest_result
                                        logger.info(f"  💎 New best: {backtest_result['trades']} trades | {backtest_result['win_rate']:.1f}% WR | PF: {backtest_result['profit_factor']:.3f}")
            
            if not best_config:
                # If no config met 55%+ threshold, find best above 50%
                logger.warning(f"  ⚠️ No config found with 55%+ WR, searching 50%+...")
                for rsi_extreme in [10, 15, 20]:
                    for min_ema_sep in [0.0005, 0.0007, 0.001]:
                        for min_momentum in [0.0003, 0.0005]:
                            config = {
                                'ema_fast': base_params['ema_fast'],
                                'ema_slow': base_params['ema_slow'],
                                'rsi_oversold': max(10, base_params['rsi_oversold'] - rsi_extreme),
                                'rsi_overbought': min(90, base_params['rsi_overbought'] + rsi_extreme),
                                'atr_multiplier': base_params['atr_multiplier'],
                                'risk_reward_ratio': 3.0,
                                'filters': {
                                    'rsi_extreme': rsi_extreme,
                                    'min_ema_separation': min_ema_sep,
                                    'min_momentum': min_momentum,
                                    'trend_strength': 0.75,
                                    'volatility_filter': True
                                }
                            }
                            backtest_result = self._backtest_ultra_selective(pair, config, df.copy())
                            if backtest_result['trades'] >= 10:
                                score = backtest_result['win_rate'] * 150 + (backtest_result['profit_factor'] - 1.0) * 200
                                if score > best_score:
                                    best_score = score
                                    best_config = config
                                    best_backtest = backtest_result
            
            if not best_config:
                best_config = base_params
                best_config['filters'] = {'rsi_extreme': 0, 'min_ema_separation': 0, 'min_momentum': 0, 'trend_strength': 0, 'volatility_filter': False}
                best_backtest = self._backtest_ultra_selective(pair, best_config, df.copy())
            
            logger.info(f"  🏆 Final: {best_backtest['trades']} trades | {best_backtest['win_rate']:.1f}% WR | PF: {best_backtest['profit_factor']:.3f}")
            
            return {
                'status': 'ok',
                'patterns': patterns,
                'best_config': best_config,
                'backtest_results': best_backtest
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
            best_fast, best_slow = 2, 8
            df['ema_fast'] = df['close'].ewm(span=best_fast, adjust=False).mean()
            df['ema_slow'] = df['close'].ewm(span=best_slow, adjust=False).mean()
            trends[tf] = {'best_ema_fast': best_fast, 'best_ema_slow': best_slow, 'trend_consistency': 0.8}
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
            
            for oversold in range(10, 30, 2):
                for overbought in range(70, 90, 2):
                    oversold_mask = (df['rsi'] < oversold) & (df['rsi'].notna())
                    overbought_mask = (df['rsi'] > overbought) & (df['rsi'].notna())
                    df['price_change'] = df['close'].pct_change().shift(-1)
                    
                    oversold_periods = df[oversold_mask]
                    overbought_periods = df[overbought_mask]
                    
                    if len(oversold_periods) > 3 and len(overbought_periods) > 3:
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
            volatility[tf] = {'avg_atr': float(atr_14.mean()), 'optimal_atr_multiplier': 1.5}
        return volatility
    
    def _synthesize_strategy(self, patterns: Dict, data_by_timeframe: Dict) -> Dict:
        """Synthesize base strategy parameters"""
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
    
    def _backtest_ultra_selective(self, pair: str, config: Dict, df: pd.DataFrame) -> Dict:
        """Ultra-selective backtest with multiple confirmations"""
        try:
            # Calculate indicators
            df['ema_fast'] = df['close'].ewm(span=config['ema_fast'], adjust=False).mean()
            df['ema_slow'] = df['close'].ewm(span=config['ema_slow'], adjust=False).mean()
            
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss.replace(0, np.nan)
            df['rsi'] = 100 - (100 / (1 + rs))
            
            high_low = df['high'] - df['low']
            high_close = abs(df['high'] - df['close'].shift())
            low_close = abs(df['low'] - df['close'].shift())
            tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            df['atr'] = tr.rolling(window=14).mean()
            
            # Calculate additional indicators for confirmation
            df['momentum'] = df['close'].pct_change(periods=5)
            df['ema_separation'] = abs(df['ema_fast'] - df['ema_slow']) / df['close']
            df['volatility'] = df['close'].rolling(window=10).std()
            
            # Trend strength (consistency over recent periods)
            df['trend_dir'] = np.where(df['ema_fast'] > df['ema_slow'], 1, -1)
            df['trend_strength'] = df['trend_dir'].rolling(window=10).apply(lambda x: (x == x.iloc[-1]).sum() / len(x) if len(x) == 10 else 0)
            
            filters = config.get('filters', {})
            rsi_extreme = filters.get('rsi_extreme', 0)
            min_ema_sep = filters.get('min_ema_separation', 0)
            min_momentum = filters.get('min_momentum', 0)
            trend_strength = filters.get('trend_strength', 0)
            volatility_filter = filters.get('volatility_filter', False)
            
            # ULTRA-STRICT SIGNAL GENERATION
            df['signal'] = 'HOLD'
            
            # BUY: Multiple confirmations required
            buy_conditions = (
                (df['ema_fast'] > df['ema_slow']) &  # Uptrend
                (df['rsi'] < (config['rsi_overbought'] - rsi_extreme)) &  # RSI well below overbought
                (df['rsi'] > 30) &  # But not too low (avoid dead cat bounces)
                (df['ema_separation'] >= min_ema_sep) &  # Strong trend
                (df['momentum'] >= min_momentum) &  # Positive momentum
                (df['trend_strength'] >= trend_strength) &  # Consistent trend
                (df['rsi'].notna()) &
                (df['atr'].notna())
            )
            
            if volatility_filter:
                median_vol = df['volatility'].median()
                buy_conditions = buy_conditions & (df['volatility'] >= median_vol * 0.7) & (df['volatility'] <= median_vol * 1.5)
            
            df.loc[buy_conditions, 'signal'] = 'BUY'
            
            # SELL: Multiple confirmations required
            sell_conditions = (
                (df['ema_fast'] < df['ema_slow']) &  # Downtrend
                (df['rsi'] > (config['rsi_oversold'] + rsi_extreme)) &  # RSI well above oversold
                (df['rsi'] < 70) &  # But not too high
                (df['ema_separation'] >= min_ema_sep) &  # Strong trend
                (df['momentum'] <= -min_momentum) &  # Negative momentum
                (df['trend_strength'] >= trend_strength) &  # Consistent trend
                (df['rsi'].notna()) &
                (df['atr'].notna())
            )
            
            if volatility_filter:
                median_vol = df['volatility'].median()
                sell_conditions = sell_conditions & (df['volatility'] >= median_vol * 0.7) & (df['volatility'] <= median_vol * 1.5)
            
            df.loc[sell_conditions, 'signal'] = 'SELL'
            
            # Backtest
            spread = 0.5 if 'XAU' in pair else (0.01 if 'JPY' in pair else 0.0001)
            trades = []
            position = None
            
            for idx, row in df.iterrows():
                if pd.isna(row['signal']) or row['signal'] == 'HOLD' or pd.isna(row['atr']):
                    continue
                
                mid = row['close']
                bid = mid - (spread / 2)
                ask = mid + (spread / 2)
                
                # Close existing position if opposite signal
                if position:
                    if (position['side'] == 'BUY' and row['signal'] == 'SELL') or \
                       (position['side'] == 'SELL' and row['signal'] == 'BUY'):
                        pnl = self._calculate_pnl(position, bid, ask, pair)
                        trades.append({
                            'side': position['side'],
                            'entry_price': position['entry_price'],
                            'exit_price': bid if position['side'] == 'BUY' else ask,
                            'pnl': pnl
                        })
                        position = None
                
                # Open new position
                if row['signal'] in ['BUY', 'SELL'] and not position:
                    atr_val = row['atr']
                    
                    if row['signal'] == 'BUY':
                        entry_price = ask
                        stop_loss = entry_price - (atr_val * config['atr_multiplier'])
                        take_profit = entry_price + (atr_val * config['atr_multiplier'] * config['risk_reward_ratio'])
                    else:
                        entry_price = bid
                        stop_loss = entry_price + (atr_val * config['atr_multiplier'])
                        take_profit = entry_price - (atr_val * config['atr_multiplier'] * config['risk_reward_ratio'])
                    
                    position = {
                        'side': row['signal'],
                        'entry_price': entry_price,
                        'stop_loss': stop_loss,
                        'take_profit': take_profit
                    }
            
            # Close final position
            if position and len(df) > 0:
                final_row = df.iloc[-1]
                final_bid = final_row['close'] - (spread / 2)
                final_ask = final_row['close'] + (spread / 2)
                pnl = self._calculate_pnl(position, final_bid, final_ask, pair)
                trades.append({
                    'side': position['side'],
                    'entry_price': position['entry_price'],
                    'exit_price': final_bid if position['side'] == 'BUY' else final_ask,
                    'pnl': pnl
                })
            
            # Calculate metrics
            if not trades:
                return {'trades': 0, 'win_rate': 0, 'profit_factor': 0, 'total_profit': 0, 'status': 'ok'}
            
            wins = [t for t in trades if t['pnl'] > 0]
            losses = [t for t in trades if t['pnl'] < 0]
            
            win_rate = (len(wins) / len(trades)) * 100 if trades else 0
            gross_profit = sum(t['pnl'] for t in wins) if wins else 0
            gross_loss = abs(sum(t['pnl'] for t in losses)) if losses else 0
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
            total_profit = sum(t['pnl'] for t in trades)
            
            return {
                'trades': len(trades),
                'win_rate': win_rate,
                'profit_factor': profit_factor,
                'total_profit': total_profit,
                'status': 'ok'
            }
            
        except Exception as e:
            logger.error(f"❌ Backtest error: {e}", exc_info=True)
            return {'status': 'error', 'error': str(e), 'trades': 0, 'win_rate': 0, 'profit_factor': 0, 'total_profit': 0}
    
    def _calculate_pnl(self, position: Dict, current_bid: float, current_ask: float, pair: str) -> float:
        """Calculate P/L in pips"""
        entry = position['entry_price']
        sl = position['stop_loss']
        tp = position['take_profit']
        
        if position['side'] == 'BUY':
            if current_bid <= sl:
                exit_price = sl
            elif current_ask >= tp:
                exit_price = tp
            else:
                exit_price = current_bid
            
            if 'JPY' in pair:
                pips = (exit_price - entry) * 100
            elif 'XAU' in pair:
                pips = (exit_price - entry) * 10
            else:
                pips = (exit_price - entry) * 10000
        else:
            if current_ask >= sl:
                exit_price = sl
            elif current_bid <= tp:
                exit_price = tp
            else:
                exit_price = current_ask
            
            if 'JPY' in pair:
                pips = (entry - exit_price) * 100
            elif 'XAU' in pair:
                pips = (entry - exit_price) * 10
            else:
                pips = (entry - exit_price) * 10000
        
        return pips


def main():
    print("\n" + "="*80)
    print("🎯 MARKET PATTERN DISCOVERY V5 - 60%+ WIN RATE TARGET")
    print("="*80)
    print("🔥 ULTRA-SELECTIVE: Multiple confirmations required")
    print("="*80)
    
    if not load_credentials():
        logger.error("❌ Failed to load credentials")
        return
    
    discovery = MarketPatternDiscoveryV5(days=30)
    output_file = discovery.discover_all_pairs()
    print(f"\n✅ Complete! Results: {output_file}")


if __name__ == '__main__':
    main()

