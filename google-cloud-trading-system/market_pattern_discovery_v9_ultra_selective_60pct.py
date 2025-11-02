#!/usr/bin/env python3
"""
Market Pattern Discovery V9 - Ultra Selective 60%+ Target
Build on 47.6% success → Add multi-timeframe, multiple confirmations
Accept VERY few trades (5-15 per pair) but target 60%+ WR
"""

import os, sys, json
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import logging

repo_root = '/Users/mac/quant_system_clean/google-cloud-trading-system'
sys.path.insert(0, repo_root)
os.chdir(repo_root)

from universal_backtest_fix import load_credentials, OandaClient, get_historical_data
from src.core.telegram_notifier import TelegramNotifier

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MarketPatternDiscoveryV9:
    """V9: Ultra-selective multi-timeframe approach targeting 60%+ WR"""
    
    def __init__(self, days=90):
        self.days = days
        self.pairs = ['GBP_USD', 'XAU_USD', 'USD_JPY', 'EUR_USD', 'NZD_USD', 'AUD_USD']
        self.results = {}
        self.telegram = TelegramNotifier()
        
    def discover_all_pairs(self):
        """Ultra-selective discovery targeting 60%+"""
        start_time = datetime.now()
        self._send_telegram(f"""🎯 <b>Pattern Discovery V9 - 60%+ Ultra Selective</b>

📊 <b>{len(self.pairs)} pairs</b> | <b>{self.days} days</b>
🔥 Multi-timeframe confirmation
⭐ Build on 47.6% success → Add more filters
🎯 Target: 60%+ WR (accept 5-15 trades per pair)
🕐 {start_time.strftime('%H:%M:%S')}""", message_type="v9_start")
        
        for idx, pair in enumerate(self.pairs, 1):
            pair_start = datetime.now()
            try:
                result = self.ultra_selective_optimization(pair)
                self.results[pair] = result
                elapsed = (datetime.now() - pair_start).total_seconds() / 60
                self._send_pair_results(pair, result, idx, len(self.pairs), elapsed)
            except Exception as e:
                logger.error(f"❌ Error analyzing {pair}: {e}", exc_info=True)
                self.results[pair] = {'status': 'error', 'error': str(e)}
        
        total_time = (datetime.now() - start_time).total_seconds() / 60
        self._send_final_summary(total_time)
        
        output_file = f"pattern_discovery_v9_results_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        logger.info(f"✅ Results saved to: {output_file}")
        return output_file
    
    def _send_pair_results(self, pair: str, result: Dict, current: int, total: int, elapsed: float):
        """Send pair results"""
        if result.get('status') != 'ok':
            return
        
        backtest = result.get('final_backtest', {})
        wr = backtest.get('win_rate', 0)
        trades = backtest.get('trades', 0)
        
        icon = "🎯" if wr >= 60 else ("✅" if wr >= 50 else "⚠️")
        
        msg = f"""{icon} <b>{pair}</b> {wr:.1f}% WR

{trades} trades (ultra-selective) | {elapsed:.1f}min | {current}/{total}"""
        self._send_telegram(msg, message_type=f"pair_v9_{pair}")
    
    def _send_final_summary(self, total_minutes: float):
        """Send final summary"""
        msg = ["🎯 <b>Pattern Discovery V9 Complete</b>\n"]
        
        viable = 0
        total_trades = 0
        sixty_plus = []
        
        for pair, result in self.results.items():
            if result.get('status') == 'ok':
                backtest = result.get('final_backtest', {})
                trades = backtest.get('trades', 0)
                wr = backtest.get('win_rate', 0)
                
                if trades > 0:
                    viable += 1
                    total_trades += trades
                    if wr >= 60:
                        sixty_plus.append(f"{pair}: {wr:.1f}%")
                    msg.append(f"<b>{pair}:</b> {trades} trades | {wr:.1f}% WR")
        
        msg.append(f"\n✅ {viable}/6 viable | 📊 {total_trades} trades")
        if sixty_plus:
            msg.append(f"🎯 60%+ WR ACHIEVED: {', '.join(sixty_plus)}")
        msg.append(f"⏱️ {total_minutes:.1f} min")
        
        self._send_telegram("\n".join(msg), message_type="v9_complete")
    
    def _send_telegram(self, message: str, message_type: str = "general"):
        """Send to Telegram"""
        try:
            self.telegram.send_message(message, message_type=message_type)
        except Exception as e:
            logger.warning(f"⚠️ Telegram failed: {e}")
    
    def ultra_selective_optimization(self, pair: str) -> Dict:
        """Ultra-selective optimization with multiple confirmations"""
        logger.info(f"\n{'='*80}\n🎯 Ultra-Selective Optimization: {pair}\n{'='*80}")
        
        client = OandaClient()
        
        # Get multiple timeframes for confirmation
        m5_candles = get_historical_data(client, pair, days=self.days, granularity='M5')
        m15_candles = get_historical_data(client, pair, days=self.days, granularity='M15')
        h1_candles = get_historical_data(client, pair, days=self.days, granularity='H1')
        
        if not m5_candles or len(m5_candles) < 500:
            return {'status': 'insufficient_data'}
        
        df_m5 = self._candles_to_dataframe(m5_candles)
        df_m15 = self._candles_to_dataframe(m15_candles) if m15_candles else None
        df_h1 = self._candles_to_dataframe(h1_candles) if h1_candles else None
        
        logger.info(f"  📊 M5: {len(df_m5)} candles")
        if df_m15 is not None:
            logger.info(f"  📊 M15: {len(df_m15)} candles")
        if df_h1 is not None:
            logger.info(f"  📊 H1: {len(df_h1)} candles")
        
        # Test various ultra-strict combinations
        best_config = None
        best_score = -999999
        best_backtest = None
        
        # Start from V4's successful pattern (47.6% for XAU_USD)
        # Test: RSI extremes, strong trends, momentum, multi-timeframe alignment
        
        for rsi_lo in [15, 20, 25, 30]:
            for rsi_hi in [70, 75, 80]:
                for min_ema_sep in [0.0005, 0.0007, 0.001, 0.0015]:
                    for min_momentum in [0.0003, 0.0005, 0.0007]:
                        for require_higher_tf in [True, False]:
                            config = {
                                'ema_fast': 2,
                                'ema_slow': 8,
                                'rsi_oversold': rsi_lo,
                                'rsi_overbought': rsi_hi,
                                'atr_multiplier': 1.5,
                                'risk_reward_ratio': 3.0,
                                'filters': {
                                    'min_ema_separation': min_ema_sep,
                                    'min_momentum': min_momentum,
                                    'require_higher_tf_alignment': require_higher_tf,
                                    'rsi_extreme_threshold': 5
                                }
                            }
                            
                            backtest_result = self._backtest_ultra_selective(
                                pair, config, df_m5, df_m15, df_h1
                            )
                            
                            # Prioritize win rate heavily - need 55%+ minimum, prefer 60%+
                            if backtest_result['trades'] >= 5:  # Minimum viable
                                if backtest_result['win_rate'] >= 55:
                                    score = (
                                        backtest_result['win_rate'] * 300 +  # Heavy weight on WR
                                        (backtest_result['profit_factor'] - 1.0) * 500 +
                                        min(backtest_result['trades'] / 2, 30) -  # Prefer 10-15 trades
                                        (abs(backtest_result['total_profit']) / 100 if backtest_result['total_profit'] < 0 else 0)
                                    )
                                    
                                    if score > best_score:
                                        best_score = score
                                        best_config = config
                                        best_backtest = backtest_result
                                        logger.info(f"  💎 New best: {backtest_result['trades']} trades | {backtest_result['win_rate']:.1f}% WR | PF: {backtest_result['profit_factor']:.3f}")
        
        if not best_config:
            # Fallback: relax to 50%+
            logger.warning(f"  ⚠️ No config with 55%+ WR found, searching 50%+...")
            for rsi_lo in [15, 20, 25]:
                for rsi_hi in [75, 80]:
                    for min_ema_sep in [0.0007, 0.001]:
                        config = {
                            'ema_fast': 2,
                            'ema_slow': 8,
                            'rsi_oversold': rsi_lo,
                            'rsi_overbought': rsi_hi,
                            'atr_multiplier': 1.5,
                            'risk_reward_ratio': 3.0,
                            'filters': {
                                'min_ema_separation': min_ema_sep,
                                'min_momentum': 0.0005,
                                'require_higher_tf_alignment': True,
                                'rsi_extreme_threshold': 5
                            }
                        }
                        backtest_result = self._backtest_ultra_selective(
                            pair, config, df_m5, df_m15, df_h1
                        )
                        if backtest_result['trades'] >= 5 and backtest_result['win_rate'] >= 50:
                            score = backtest_result['win_rate'] * 200 + (backtest_result['profit_factor'] - 1.0) * 300
                            if score > best_score:
                                best_score = score
                                best_config = config
                                best_backtest = backtest_result
        
        if not best_config:
            # Ultimate fallback
            best_config = {
                'ema_fast': 2,
                'ema_slow': 8,
                'rsi_oversold': 20,
                'rsi_overbought': 80,
                'atr_multiplier': 1.5,
                'risk_reward_ratio': 3.0,
                'filters': {}
            }
            best_backtest = self._backtest_ultra_selective(pair, best_config, df_m5, df_m15, df_h1)
        
        logger.info(f"  🏆 Final: {best_backtest['trades']} trades | {best_backtest['win_rate']:.1f}% WR | PF: {best_backtest['profit_factor']:.3f}")
        
        return {
            'status': 'ok',
            'best_config': best_config,
            'final_backtest': best_backtest
        }
    
    def _backtest_ultra_selective(self, pair: str, config: Dict, df_m5: pd.DataFrame, 
                                  df_m15: Optional[pd.DataFrame], df_h1: Optional[pd.DataFrame]) -> Dict:
        """Ultra-selective backtest with multi-timeframe confirmation"""
        try:
            df = df_m5.copy()
            
            # Calculate indicators on M5
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
            df['momentum'] = df['close'].pct_change(periods=5)
            df['ema_separation'] = abs(df['ema_fast'] - df['ema_slow']) / df['close']
            
            # Higher timeframe alignment (if available)
            df['higher_tf_trend'] = 0  # Neutral
            if df_m15 is not None:
                df_m15_aligned = df_m15.copy()
                df_m15_aligned['ema_fast'] = df_m15_aligned['close'].ewm(span=config['ema_fast'], adjust=False).mean()
                df_m15_aligned['ema_slow'] = df_m15_aligned['close'].ewm(span=config['ema_slow'], adjust=False).mean()
                df_m15_aligned['trend'] = np.where(df_m15_aligned['ema_fast'] > df_m15_aligned['ema_slow'], 1, -1)
                
                # Resample to M5 timeframe
                df_m15_resampled = df_m15_aligned.resample('5T').ffill()
                df = df.join(df_m15_resampled[['trend']], rsuffix='_m15', how='left')
                df['higher_tf_trend'] = df['trend_m15'].fillna(0)
            
            filters = config.get('filters', {})
            min_ema_sep = filters.get('min_ema_separation', 0)
            min_momentum = filters.get('min_momentum', 0)
            require_higher_tf = filters.get('require_higher_tf_alignment', False)
            rsi_extreme = filters.get('rsi_extreme_threshold', 0)
            
            # ULTRA-STRICT signal generation
            df['signal'] = 'HOLD'
            
            # BUY: Multiple confirmations
            buy_conditions = (
                (df['ema_fast'] > df['ema_slow']) &  # Uptrend
                (df['rsi'] < (config['rsi_overbought'] - rsi_extreme)) &  # RSI well below overbought
                (df['rsi'] > 30) &  # But not too extreme
                (df['ema_separation'] >= min_ema_sep) &  # Strong trend
                (df['momentum'] >= min_momentum) &  # Positive momentum
                (df['rsi'].notna()) &
                (df['atr'].notna())
            )
            
            if require_higher_tf:
                buy_conditions = buy_conditions & (df['higher_tf_trend'] >= 0)  # Higher TF aligned or neutral
            
            df.loc[buy_conditions, 'signal'] = 'BUY'
            
            # SELL: Multiple confirmations
            sell_conditions = (
                (df['ema_fast'] < df['ema_slow']) &  # Downtrend
                (df['rsi'] > (config['rsi_oversold'] + rsi_extreme)) &  # RSI well above oversold
                (df['rsi'] < 70) &  # But not too extreme
                (df['ema_separation'] >= min_ema_sep) &  # Strong trend
                (df['momentum'] <= -min_momentum) &  # Negative momentum
                (df['rsi'].notna()) &
                (df['atr'].notna())
            )
            
            if require_higher_tf:
                sell_conditions = sell_conditions & (df['higher_tf_trend'] <= 0)  # Higher TF aligned or neutral
            
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
                
                if position:
                    if (position['side'] == 'BUY' and row['signal'] == 'SELL') or \
                       (position['side'] == 'SELL' and row['signal'] == 'BUY'):
                        pnl = self._calculate_pnl(position, bid, ask, pair)
                        trades.append({'side': position['side'], 'entry_price': position['entry_price'], 'pnl': pnl})
                        position = None
                
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
                trades.append({'side': position['side'], 'entry_price': position['entry_price'], 'pnl': pnl})
            
            if not trades:
                return {'trades': 0, 'win_rate': 0, 'profit_factor': 0, 'total_profit': 0, 'status': 'ok'}
            
            wins = [t for t in trades if t['pnl'] > 0]
            losses = [t for t in trades if t['pnl'] <= 0]
            
            win_rate = (len(wins) / len(trades)) * 100 if trades else 0
            gross_profit = sum(t['pnl'] for t in wins) if wins else 0
            gross_loss = abs(sum(t['pnl'] for t in losses)) if losses else 0
            pf = gross_profit / gross_loss if gross_loss > 0 else 0
            total_pnl = sum(t['pnl'] for t in trades)
            
            return {
                'trades': len(trades),
                'win_rate': win_rate,
                'profit_factor': pf,
                'total_profit': total_pnl,
                'status': 'ok'
            }
            
        except Exception as e:
            logger.error(f"❌ Backtest error: {e}", exc_info=True)
            return {'status': 'error', 'error': str(e), 'trades': 0, 'win_rate': 0, 'profit_factor': 0, 'total_profit': 0}
    
    def _calculate_pnl(self, position: Dict, current_bid: float, current_ask: float, pair: str) -> float:
        """Calculate P/L"""
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
        else:
            if current_ask >= sl:
                exit_price = sl
            elif current_bid <= tp:
                exit_price = tp
            else:
                exit_price = current_ask
        
        if 'JPY' in pair:
            pips = ((exit_price - entry) * 100) if position['side'] == 'BUY' else ((entry - exit_price) * 100)
        elif 'XAU' in pair:
            pips = ((exit_price - entry) * 10) if position['side'] == 'BUY' else ((entry - exit_price) * 10)
        else:
            pips = ((exit_price - entry) * 10000) if position['side'] == 'BUY' else ((entry - exit_price) * 10000)
        
        return pips
    
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


def main():
    print("\n" + "="*80)
    print("🎯 MARKET PATTERN DISCOVERY V9 - ULTRA SELECTIVE 60%+")
    print("="*80)
    print("Multi-timeframe confirmation + Ultra-strict filters")
    print("="*80)
    
    if not load_credentials():
        logger.error("❌ Failed to load credentials")
        return
    
    discovery = MarketPatternDiscoveryV9(days=90)
    output_file = discovery.discover_all_pairs()
    print(f"\n✅ Complete! Results: {output_file}")


if __name__ == '__main__':
    main()

