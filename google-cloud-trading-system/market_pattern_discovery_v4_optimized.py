#!/usr/bin/env python3
"""
Market Pattern Discovery V4 - Win Rate Optimized
Each pair tested on its own merits with quality filters to improve win rates
"""

import os, sys, json
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import pytz
import logging

repo_root = '/Users/mac/quant_system_clean/google-cloud-trading-system'
sys.path.insert(0, repo_root)
os.chdir(repo_root)

from universal_backtest_fix import load_credentials, OandaClient, get_historical_data
from src.core.telegram_notifier import TelegramNotifier

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MarketPatternDiscoveryV4:
    """V4: Win-rate optimized with quality filters - each pair tested individually"""
    
    def __init__(self, days=30):
        self.days = days
        self.pairs = ['GBP_USD', 'XAU_USD', 'USD_JPY', 'EUR_USD', 'NZD_USD', 'AUD_USD']
        self.timeframes = ['M5', 'M15', 'H1']
        self.results = {}
        self.telegram = TelegramNotifier()
        
    def discover_all_pairs(self):
        """Discover and optimize each pair individually"""
        start_time = datetime.now()
        self._send_telegram(f"""🔍 <b>Pattern Discovery V4 - Win Rate Optimized</b>

📊 <b>{len(self.pairs)} pairs</b> | <b>{self.days} days</b>
🎯 Each pair optimized individually
⭐ Focus: Improve win rates + Quality filters
🕐 {start_time.strftime('%H:%M:%S')}""", message_type="v4_start")
        
        for idx, pair in enumerate(self.pairs, 1):
            pair_start = datetime.now()
            try:
                result = self.optimize_pair_individual(pair)
                self.results[pair] = result
                elapsed = (datetime.now() - pair_start).total_seconds() / 60
                self._send_pair_results(pair, result, idx, len(self.pairs), elapsed)
            except Exception as e:
                logger.error(f"❌ Error optimizing {pair}: {e}", exc_info=True)
                self.results[pair] = {'status': 'error', 'error': str(e)}
        
        total_time = (datetime.now() - start_time).total_seconds() / 60
        self._send_final_summary(total_time)
        
        output_file = f"pattern_discovery_v4_results_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
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
            
            status_msg = f"""✅ <b>{pair} Optimized</b>

<b>📊 Best Config:</b>
EMA({best_config.get('ema_fast')}/{best_config.get('ema_slow')}) RSI({best_config.get('rsi_oversold')}-{best_config.get('rsi_overbought')})
ATRx{best_config.get('atr_multiplier', 0):.2f} RR={best_config.get('risk_reward_ratio', 0):.1f}

<b>🎯 Filters:</b>
RSI Threshold: {filters.get('rsi_threshold', 0):.0f}% | EMA Separation: {filters.get('min_ema_separation', 0):.4f}
Momentum: {filters.get('min_momentum', 0):.4f}

<b>🧪 Results:</b>
{trades} trades | {wr:.1f}% WR | PF: {pf:.3f} | {pnl:.1f} pips

⏱️ {elapsed:.1f}min | {current}/{total}"""
        
        self._send_telegram(status_msg, message_type=f"pair_v4_{pair}")
    
    def _send_final_summary(self, total_minutes: float):
        """Send final summary"""
        msg = ["🎉 <b>Pattern Discovery V4 Complete</b>\n"]
        
        viable = 0
        total_trades = 0
        good_wr = []
        best_pairs = []
        
        for pair, result in self.results.items():
            if result.get('status') == 'ok':
                backtest = result.get('backtest_results', {})
                trades = backtest.get('trades', 0)
                wr = backtest.get('win_rate', 0)
                pf = backtest.get('profit_factor', 0)
                
                if trades > 0:
                    viable += 1
                    total_trades += trades
                    if wr >= 35:
                        good_wr.append(f"{pair}: {wr:.1f}%")
                    if pf >= 1.2 and wr >= 30:
                        best_pairs.append(f"{pair} (WR:{wr:.1f}% PF:{pf:.2f})")
                    msg.append(f"<b>{pair}:</b> {trades} trades | {wr:.1f}% WR | PF: {pf:.3f}")
        
        msg.append(f"\n✅ {viable}/6 viable | 📊 {total_trades} total trades")
        if good_wr:
            msg.append(f"⭐ 35%+ WR: {', '.join(good_wr)}")
        if best_pairs:
            msg.append(f"🏆 Best: {', '.join(best_pairs)}")
        msg.append(f"⏱️ {total_minutes:.1f} minutes")
        
        self._send_telegram("\n".join(msg), message_type="v4_complete")
    
    def _send_telegram(self, message: str, message_type: str = "general"):
        """Send to Telegram"""
        try:
            self.telegram.send_message(message, message_type=message_type)
        except Exception as e:
            logger.warning(f"⚠️ Telegram failed: {e}")
    
    def optimize_pair_individual(self, pair: str) -> Dict:
        """Optimize each pair individually with quality filters"""
        logger.info(f"\n{'='*80}\n🔍 Optimizing {pair} (Individual Testing)\n{'='*80}")
        
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
            # Discover base patterns
            patterns = {
                'trend_analysis': self._analyze_trends(data_by_timeframe, pair),
                'rsi_analysis': self._analyze_rsi_levels(data_by_timeframe, pair),
                'volatility_analysis': self._analyze_volatility(data_by_timeframe, pair),
            }
            
            # Test multiple configurations with different quality filters
            best_config = None
            best_score = -999999
            best_backtest = None
            
            primary_tf = 'M5' if 'M5' in data_by_timeframe else list(data_by_timeframe.keys())[0]
            df = data_by_timeframe[primary_tf]
            
            # Base parameters from patterns
            base_params = self._synthesize_strategy(patterns, data_by_timeframe)
            
            # Test different filter combinations for THIS specific pair
            rsi_oversold = patterns['rsi_analysis'].get(primary_tf, {}).get('optimal_oversold', 20)
            rsi_overbought = patterns['rsi_analysis'].get(primary_tf, {}).get('optimal_overbought', 80)
            
            # Optimize filters for THIS pair
            for rsi_threshold in [5, 10, 15]:  # How extreme RSI must be
                for min_ema_sep in [0.0001, 0.0002, 0.0003, 0.0005]:  # Minimum EMA separation
                    for min_momentum in [0.0, 0.0001, 0.0002]:  # Momentum filter
                        config = {
                            'ema_fast': base_params['ema_fast'],
                            'ema_slow': base_params['ema_slow'],
                            'rsi_oversold': max(15, rsi_oversold - rsi_threshold),
                            'rsi_overbought': min(85, rsi_overbought + rsi_threshold),
                            'atr_multiplier': base_params['atr_multiplier'],
                            'risk_reward_ratio': base_params['risk_reward_ratio'],
                            'filters': {
                                'rsi_threshold': rsi_threshold,
                                'min_ema_separation': min_ema_sep,
                                'min_momentum': min_momentum
                            }
                        }
                        
                        backtest_result = self._backtest_with_filters(pair, config, df.copy())
                        
                        if backtest_result['trades'] >= 10:  # Minimum viable trades
                            # Score: Prioritize win rate and profit factor
                            score = (
                                backtest_result['win_rate'] * 100 +  # Win rate weight
                                (backtest_result['profit_factor'] - 1.0) * 500 +  # PF weight
                                min(backtest_result['trades'] / 2, 50) -  # Trade count (capped)
                                (abs(backtest_result['total_profit']) / 100 if backtest_result['total_profit'] < 0 else 0)  # Penalty for losses
                            )
                            
                            if score > best_score:
                                best_score = score
                                best_config = config
                                best_backtest = backtest_result
            
            if not best_config:
                # Fallback to base config
                best_config = base_params
                best_config['filters'] = {'rsi_threshold': 0, 'min_ema_separation': 0, 'min_momentum': 0}
                best_backtest = self._backtest_with_filters(pair, best_config, df.copy())
            
            logger.info(f"  🏆 Best for {pair}: {best_backtest['trades']} trades | {best_backtest['win_rate']:.1f}% WR | PF: {best_backtest['profit_factor']:.3f}")
            
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
            optimal_multiplier = 1.5
            volatility[tf] = {
                'avg_atr': avg_atr,
                'optimal_atr_multiplier': float(optimal_multiplier)
            }
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
    
    def _backtest_with_filters(self, pair: str, config: Dict, df: pd.DataFrame) -> Dict:
        """Backtest with quality filters"""
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
            
            # Calculate momentum (price change over recent periods)
            df['momentum'] = df['close'].pct_change(periods=5)
            
            # Calculate EMA separation
            df['ema_separation'] = abs(df['ema_fast'] - df['ema_slow']) / df['close']
            
            filters = config.get('filters', {})
            rsi_threshold = filters.get('rsi_threshold', 0)
            min_ema_sep = filters.get('min_ema_separation', 0)
            min_momentum = filters.get('min_momentum', 0)
            
            # Generate signals with QUALITY FILTERS
            df['signal'] = 'HOLD'
            
            # BUY: Uptrend + RSI not overbought + Quality filters
            buy_mask = (
                (df['ema_fast'] > df['ema_slow']) &  # Uptrend
                (df['rsi'] < (config['rsi_overbought'] - rsi_threshold)) &  # RSI not extreme
                (df['rsi'].notna()) &
                (df['atr'].notna()) &
                (df['ema_separation'] >= min_ema_sep) &  # Strong trend
                (df['momentum'] >= min_momentum)  # Positive momentum
            )
            df.loc[buy_mask, 'signal'] = 'BUY'
            
            # SELL: Downtrend + RSI not oversold + Quality filters
            sell_mask = (
                (df['ema_fast'] < df['ema_slow']) &  # Downtrend
                (df['rsi'] > (config['rsi_oversold'] + rsi_threshold)) &  # RSI not extreme
                (df['rsi'].notna()) &
                (df['atr'].notna()) &
                (df['ema_separation'] >= min_ema_sep) &  # Strong trend
                (df['momentum'] <= -min_momentum)  # Negative momentum
            )
            df.loc[sell_mask, 'signal'] = 'SELL'
            
            # Convert to candles and backtest
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
                            'pnl': pnl,
                            'hit_sl': pnl < 0,
                            'hit_tp': pnl > 0
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
                    'pnl': pnl,
                    'hit_sl': pnl < 0,
                    'hit_tp': pnl > 0
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
    print("🔍 MARKET PATTERN DISCOVERY V4 - WIN RATE OPTIMIZED")
    print("="*80)
    print("✅ Each pair tested on its own merits with individual optimization")
    print("="*80)
    
    if not load_credentials():
        logger.error("❌ Failed to load credentials")
        return
    
    discovery = MarketPatternDiscoveryV4(days=30)
    output_file = discovery.discover_all_pairs()
    print(f"\n✅ Complete! Results: {output_file}")


if __name__ == '__main__':
    main()

