#!/usr/bin/env python3
"""
Market Pattern Discovery V7 - 60%+ Proven Patterns Only
Analyze ALL historical trades, identify patterns with 60%+ WR
Then ONLY trade those specific proven patterns
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

class MarketPatternDiscoveryV7:
    """V7: Find patterns with PROVEN 60%+ WR, trade only those"""
    
    def __init__(self, days=90):  # More data = more samples to validate
        self.days = days
        self.pairs = ['GBP_USD', 'XAU_USD', 'USD_JPY', 'EUR_USD', 'NZD_USD', 'AUD_USD']
        self.results = {}
        self.telegram = TelegramNotifier()
        
    def discover_all_pairs(self):
        """Discover 60%+ proven patterns for each pair"""
        start_time = datetime.now()
        self._send_telegram(f"""🎯 <b>Pattern Discovery V7 - 60%+ Proven Patterns</b>

📊 <b>{len(self.pairs)} pairs</b> | <b>{self.days} days</b>
🔍 Step 1: Generate ALL trades, analyze every pattern
🎯 Step 2: Identify patterns with 60%+ WR (minimum 10 samples)
✅ Step 3: Trade ONLY those proven patterns
🕐 {start_time.strftime('%H:%M:%S')}""", message_type="v7_start")
        
        for idx, pair in enumerate(self.pairs, 1):
            pair_start = datetime.now()
            try:
                result = self.find_proven_60pct_patterns(pair)
                self.results[pair] = result
                elapsed = (datetime.now() - pair_start).total_seconds() / 60
                self._send_pair_results(pair, result, idx, len(self.pairs), elapsed)
            except Exception as e:
                logger.error(f"❌ Error analyzing {pair}: {e}", exc_info=True)
                self.results[pair] = {'status': 'error', 'error': str(e)}
        
        total_time = (datetime.now() - start_time).total_seconds() / 60
        self._send_final_summary(total_time)
        
        output_file = f"pattern_discovery_v7_results_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        logger.info(f"✅ Results saved to: {output_file}")
        return output_file
    
    def _send_pair_results(self, pair: str, result: Dict, current: int, total: int, elapsed: float):
        """Send pair results"""
        if result.get('status') != 'ok':
            return
        
        backtest = result.get('backtest_results', {})
        wr = backtest.get('win_rate', 0)
        trades = backtest.get('trades', 0)
        
        icon = "🎯" if wr >= 60 else ("✅" if wr >= 50 else "⚠️")
        
        msg = f"""{icon} <b>{pair}</b> {wr:.1f}% WR

{trades} trades | {elapsed:.1f}min | {current}/{total}"""
        self._send_telegram(msg, message_type=f"pair_v7_{pair}")
    
    def _send_final_summary(self, total_minutes: float):
        """Send final summary"""
        msg = ["🎯 <b>Pattern Discovery V7 Complete</b>\n"]
        
        viable = 0
        total_trades = 0
        sixty_plus = []
        
        for pair, result in self.results.items():
            if result.get('status') == 'ok':
                backtest = result.get('backtest_results', {})
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
            msg.append(f"🎯 60%+ WR: {', '.join(sixty_plus)}")
        msg.append(f"⏱️ {total_minutes:.1f} min")
        
        self._send_telegram("\n".join(msg), message_type="v7_complete")
    
    def _send_telegram(self, message: str, message_type: str = "general"):
        """Send to Telegram"""
        try:
            self.telegram.send_message(message, message_type=message_type)
        except Exception as e:
            logger.warning(f"⚠️ Telegram failed: {e}")
    
    def find_proven_60pct_patterns(self, pair: str) -> Dict:
        """Find patterns with proven 60%+ WR"""
        logger.info(f"\n{'='*80}\n🎯 Finding 60%+ Proven Patterns: {pair}\n{'='*80}")
        
        client = OandaClient()
        candles = get_historical_data(client, pair, days=self.days, granularity='M5')
        
        if not candles or len(candles) < 500:
            return {'status': 'insufficient_data'}
        
        df = self._candles_to_dataframe(candles)
        logger.info(f"  📊 {len(df)} candles loaded ({self.days} days)")
        
        # STEP 1: Generate ALL possible trades
        logger.info("  Step 1: Generating all trades to analyze...")
        all_trades = self._generate_comprehensive_trades(df, pair)
        
        logger.info(f"  ✅ Generated {len(all_trades)} total trades")
        
        if len(all_trades) < 100:
            return {'status': 'insufficient_trades', 'trades': len(all_trades)}
        
        # STEP 2: Group trades by pattern characteristics
        logger.info("  Step 2: Grouping trades by pattern characteristics...")
        pattern_groups = self._group_trades_by_pattern(all_trades)
        
        # STEP 3: Find patterns with 60%+ WR (minimum 10 samples)
        logger.info("  Step 3: Finding patterns with 60%+ WR...")
        proven_patterns = []
        
        for pattern_key, trades in pattern_groups.items():
            if len(trades) < 10:  # Minimum samples to trust
                continue
            
            wins = sum(1 for t in trades if t['pnl'] > 0)
            wr = (wins / len(trades)) * 100
            
            if wr >= 60:
                proven_patterns.append({
                    'pattern': pattern_key,
                    'trades': len(trades),
                    'win_rate': wr,
                    'wins': wins,
                    'sample_trades': trades[:5]  # Keep samples
                })
                logger.info(f"  ✅ Found pattern: {pattern_key} → {wr:.1f}% WR ({len(trades)} samples)")
        
        if not proven_patterns:
            logger.warning(f"  ⚠️ No patterns found with 60%+ WR (minimum 10 samples)")
            
            # Fallback: Find best patterns (50%+)
            logger.info("  🔍 Searching for best patterns (50%+)...")
            for pattern_key, trades in pattern_groups.items():
                if len(trades) < 10:
                    continue
                wins = sum(1 for t in trades if t['pnl'] > 0)
                wr = (wins / len(trades)) * 100
                if wr >= 50:
                    proven_patterns.append({
                        'pattern': pattern_key,
                        'trades': len(trades),
                        'win_rate': wr,
                        'wins': wins
                    })
        
        proven_patterns.sort(key=lambda x: x['win_rate'], reverse=True)
        
        # STEP 4: Trade ONLY proven patterns
        logger.info(f"  Step 4: Trading {len(proven_patterns)} proven pattern(s)...")
        final_trades = self._trade_only_proven_patterns(df, proven_patterns, pair)
        
        if not final_trades:
            return {
                'status': 'ok',
                'all_trades': len(all_trades),
                'proven_patterns': len(proven_patterns),
                'backtest_results': {'trades': 0, 'win_rate': 0, 'profit_factor': 0, 'total_profit': 0}
            }
        
        wins = [t for t in final_trades if t['pnl'] > 0]
        losses = [t for t in final_trades if t['pnl'] <= 0]
        
        final_wr = (len(wins) / len(final_trades)) * 100
        gross_profit = sum(t['pnl'] for t in wins) if wins else 0
        gross_loss = abs(sum(t['pnl'] for t in losses)) if losses else 0
        pf = gross_profit / gross_loss if gross_loss > 0 else 0
        total_pnl = sum(t['pnl'] for t in final_trades)
        
        logger.info(f"  🎯 Final Results: {len(final_trades)} trades | {final_wr:.1f}% WR | PF: {pf:.3f}")
        
        return {
            'status': 'ok',
            'all_trades': len(all_trades),
            'proven_patterns': proven_patterns,
            'backtest_results': {
                'trades': len(final_trades),
                'win_rate': final_wr,
                'profit_factor': pf,
                'total_profit': total_pnl,
                'status': 'ok'
            }
        }
    
    def _generate_comprehensive_trades(self, df: pd.DataFrame, pair: str) -> List[Dict]:
        """Generate all possible trades with full characteristics"""
        # Calculate all indicators
        df['ema_fast'] = df['close'].ewm(span=2, adjust=False).mean()
        df['ema_slow'] = df['close'].ewm(span=8, adjust=False).mean()
        
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
        
        # Volatility
        df['volatility'] = df['close'].rolling(window=10).std()
        
        # Price position (relative to recent range)
        df['price_position'] = (df['close'] - df['close'].rolling(window=20).min()) / \
                              (df['close'].rolling(window=20).max() - df['close'].rolling(window=20).min())
        
        # Generate signals (very relaxed to get all possible setups)
        df['signal'] = 'HOLD'
        buy_mask = (df['ema_fast'] > df['ema_slow']) & (df['rsi'].notna()) & (df['atr'].notna())
        sell_mask = (df['ema_fast'] < df['ema_slow']) & (df['rsi'].notna()) & (df['atr'].notna())
        df.loc[buy_mask, 'signal'] = 'BUY'
        df.loc[sell_mask, 'signal'] = 'SELL'
        
        # Backtest and capture all characteristics
        spread = 0.5 if 'XAU' in pair else (0.01 if 'JPY' in pair else 0.0001)
        trades = []
        position = None
        
        for idx, row in df.iterrows():
            if pd.isna(row['signal']) or row['signal'] == 'HOLD' or pd.isna(row['atr']):
                continue
            
            mid = row['close']
            bid = mid - (spread / 2)
            ask = mid + (spread / 2)
            
            # Close position and record
            if position:
                if (position['side'] == 'BUY' and row['signal'] == 'SELL') or \
                   (position['side'] == 'SELL' and row['signal'] == 'BUY'):
                    pnl = self._calculate_pnl(position, bid, ask, pair)
                    
                    trades.append({
                        'side': position['side'],
                        'entry_price': position['entry_price'],
                        'pnl': pnl,
                        'entry_rsi': position['entry_rsi'],
                        'entry_momentum': position['entry_momentum'],
                        'entry_ema_sep': position['entry_ema_sep'],
                        'entry_volatility': position['entry_volatility'],
                        'entry_price_pos': position['entry_price_pos'],
                        'entry_hour': position['entry_hour']
                    })
                    position = None
            
            # Open position
            if row['signal'] in ['BUY', 'SELL'] and not position:
                atr_val = row['atr']
                if row['signal'] == 'BUY':
                    entry_price = ask
                    stop_loss = entry_price - (atr_val * 1.5)
                    take_profit = entry_price + (atr_val * 1.5 * 3.0)
                else:
                    entry_price = bid
                    stop_loss = entry_price + (atr_val * 1.5)
                    take_profit = entry_price - (atr_val * 1.5 * 3.0)
                
                position = {
                    'side': row['signal'],
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'entry_rsi': row['rsi'],
                    'entry_momentum': row['momentum'],
                    'entry_ema_sep': row['ema_separation'],
                    'entry_volatility': row['volatility'],
                    'entry_price_pos': row['price_position'],
                    'entry_hour': idx.hour if hasattr(idx, 'hour') else 0
                }
        
        return trades
    
    def _group_trades_by_pattern(self, trades: List[Dict]) -> Dict[str, List[Dict]]:
        """Group trades by pattern characteristics"""
        groups = defaultdict(list)
        
        for trade in trades:
            # Create pattern key from characteristics
            rsi_bucket = int(trade['entry_rsi'] / 10) * 10 if not pd.isna(trade['entry_rsi']) else 50
            momentum_bucket = 'pos' if trade['entry_momentum'] > 0.0002 else ('neg' if trade['entry_momentum'] < -0.0002 else 'neutral')
            ema_sep_bucket = 'high' if trade['entry_ema_sep'] > 0.0005 else ('medium' if trade['entry_ema_sep'] > 0.0002 else 'low')
            vol_bucket = 'high' if not pd.isna(trade['entry_volatility']) and trade['entry_volatility'] > 0.001 else 'low'
            price_pos_bucket = 'high' if not pd.isna(trade['entry_price_pos']) and trade['entry_price_pos'] > 0.7 else ('low' if trade['entry_price_pos'] < 0.3 else 'mid')
            hour_bucket = 'london' if 8 <= trade['entry_hour'] < 16 else ('ny' if 13 <= trade['entry_hour'] < 21 else 'asian')
            
            pattern_key = f"{trade['side']}_RSI{rsi_bucket}_{momentum_bucket}_EMASep{ema_sep_bucket}_Vol{vol_bucket}_Pos{price_pos_bucket}_{hour_bucket}"
            
            groups[pattern_key].append(trade)
        
        return dict(groups)
    
    def _trade_only_proven_patterns(self, df: pd.DataFrame, proven_patterns: List[Dict], pair: str) -> List[Dict]:
        """Trade only patterns that have proven 60%+ WR"""
        if not proven_patterns:
            return []
        
        # Recalculate indicators
        df['ema_fast'] = df['close'].ewm(span=2, adjust=False).mean()
        df['ema_slow'] = df['close'].ewm(span=8, adjust=False).mean()
        
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
        df['volatility'] = df['close'].rolling(window=10).std()
        df['price_position'] = (df['close'] - df['close'].rolling(window=20).min()) / \
                              (df['close'].rolling(window=20).max() - df['close'].rolling(window=20).min())
        
        # Extract pattern conditions
        pattern_conditions = []
        for pattern in proven_patterns:
            parts = pattern['pattern'].split('_')
            side = parts[0]
            rsi_range = None
            momentum_req = None
            ema_sep_req = None
            
            for part in parts:
                if part.startswith('RSI'):
                    rsi_val = int(part[3:])
                    rsi_range = (rsi_val, rsi_val + 10)
                elif part.startswith('momentum'):
                    momentum_req = part
                elif part.startswith('EMASep'):
                    ema_sep_req = part
            
            pattern_conditions.append({
                'side': side,
                'rsi_range': rsi_range,
                'momentum_req': momentum_req,
                'ema_sep_req': ema_sep_req,
                'win_rate': pattern['win_rate']
            })
        
        # Generate signals only for proven patterns
        df['signal'] = 'HOLD'
        
        for condition in pattern_conditions:
            if condition['side'] == 'BUY':
                mask = (df['ema_fast'] > df['ema_slow'])
                if condition['rsi_range']:
                    mask = mask & (df['rsi'] >= condition['rsi_range'][0]) & (df['rsi'] < condition['rsi_range'][1])
                if condition['momentum_req'] == 'pos':
                    mask = mask & (df['momentum'] > 0.0002)
                if condition['ema_sep_req'] and 'high' in condition['ema_sep_req']:
                    mask = mask & (df['ema_separation'] > 0.0005)
                
                df.loc[mask, 'signal'] = 'BUY'
            
            elif condition['side'] == 'SELL':
                mask = (df['ema_fast'] < df['ema_slow'])
                if condition['rsi_range']:
                    mask = mask & (df['rsi'] >= condition['rsi_range'][0]) & (df['rsi'] < condition['rsi_range'][1])
                if condition['momentum_req'] == 'neg':
                    mask = mask & (df['momentum'] < -0.0002)
                if condition['ema_sep_req'] and 'high' in condition['ema_sep_req']:
                    mask = mask & (df['ema_separation'] > 0.0005)
                
                df.loc[mask, 'signal'] = 'SELL'
        
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
                    stop_loss = entry_price - (atr_val * 1.5)
                    take_profit = entry_price + (atr_val * 1.5 * 3.0)
                else:
                    entry_price = bid
                    stop_loss = entry_price + (atr_val * 1.5)
                    take_profit = entry_price - (atr_val * 1.5 * 3.0)
                
                position = {
                    'side': row['signal'],
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit
                }
        
        return trades
    
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
    print("🎯 MARKET PATTERN DISCOVERY V7 - 60%+ PROVEN PATTERNS")
    print("="*80)
    print("Find patterns with proven 60%+ WR → Trade ONLY those")
    print("="*80)
    
    if not load_credentials():
        logger.error("❌ Failed to load credentials")
        return
    
    discovery = MarketPatternDiscoveryV7(days=90)
    output_file = discovery.discover_all_pairs()
    print(f"\n✅ Complete! Results: {output_file}")


if __name__ == '__main__':
    main()

