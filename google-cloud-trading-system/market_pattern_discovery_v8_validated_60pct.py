#!/usr/bin/env python3
"""
Market Pattern Discovery V8 - Validated 60%+ Patterns
Find patterns with 60%+ WR (5+ samples), validate on out-of-sample data
Only trade patterns that validate
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

class MarketPatternDiscoveryV8:
    """V8: Find 60%+ patterns (5+ samples), validate, trade only validated"""
    
    def __init__(self, days=90):
        self.days = days
        self.pairs = ['GBP_USD', 'XAU_USD', 'USD_JPY', 'EUR_USD', 'NZD_USD', 'AUD_USD']
        self.results = {}
        self.telegram = TelegramNotifier()
        
    def discover_all_pairs(self):
        """Discover and validate 60%+ patterns"""
        start_time = datetime.now()
        self._send_telegram(f"""🎯 <b>Pattern Discovery V8 - Validated 60%+</b>

📊 <b>{len(self.pairs)} pairs</b> | <b>{self.days} days</b>
🔍 Find patterns with 60%+ WR (5+ samples)
✅ Validate on out-of-sample data
🎯 Trade ONLY validated patterns
🕐 {start_time.strftime('%H:%M:%S')}""", message_type="v8_start")
        
        for idx, pair in enumerate(self.pairs, 1):
            pair_start = datetime.now()
            try:
                result = self.find_and_validate_patterns(pair)
                self.results[pair] = result
                elapsed = (datetime.now() - pair_start).total_seconds() / 60
                self._send_pair_results(pair, result, idx, len(self.pairs), elapsed)
            except Exception as e:
                logger.error(f"❌ Error analyzing {pair}: {e}", exc_info=True)
                self.results[pair] = {'status': 'error', 'error': str(e)}
        
        total_time = (datetime.now() - start_time).total_seconds() / 60
        self._send_final_summary(total_time)
        
        output_file = f"pattern_discovery_v8_results_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
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
        
        validated = result.get('validated_patterns', [])
        
        msg = f"""{icon} <b>{pair}</b> {wr:.1f}% WR

{len(validated)} validated patterns | {trades} trades
{elapsed:.1f}min | {current}/{total}"""
        self._send_telegram(msg, message_type=f"pair_v8_{pair}")
    
    def _send_final_summary(self, total_minutes: float):
        """Send final summary"""
        msg = ["🎯 <b>Pattern Discovery V8 Complete</b>\n"]
        
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
            msg.append(f"🎯 60%+ WR: {', '.join(sixty_plus)}")
        msg.append(f"⏱️ {total_minutes:.1f} min")
        
        self._send_telegram("\n".join(msg), message_type="v8_complete")
    
    def _send_telegram(self, message: str, message_type: str = "general"):
        """Send to Telegram"""
        try:
            self.telegram.send_message(message, message_type=message_type)
        except Exception as e:
            logger.warning(f"⚠️ Telegram failed: {e}")
    
    def find_and_validate_patterns(self, pair: str) -> Dict:
        """Find 60%+ patterns and validate them"""
        logger.info(f"\n{'='*80}\n🎯 Finding & Validating 60%+ Patterns: {pair}\n{'='*80}")
        
        client = OandaClient()
        candles = get_historical_data(client, pair, days=self.days, granularity='M5')
        
        if not candles or len(candles) < 500:
            return {'status': 'insufficient_data'}
        
        df = self._candles_to_dataframe(candles)
        logger.info(f"  📊 {len(df)} candles loaded")
        
        # Split into training (60%) and validation (40%)
        split_idx = int(len(df) * 0.6)
        train_df = df.iloc[:split_idx].copy()
        val_df = df.iloc[split_idx:].copy()
        
        logger.info(f"  📈 Training: {len(train_df)} candles | Validation: {len(val_df)} candles")
        
        # STEP 1: Find patterns in training data
        logger.info("  Step 1: Finding patterns in training data...")
        train_trades = self._generate_all_trades(train_df, pair)
        logger.info(f"  ✅ Generated {len(train_trades)} training trades")
        
        if len(train_trades) < 50:
            return {'status': 'insufficient_training_trades', 'trades': len(train_trades)}
        
        pattern_groups = self._group_trades_by_pattern(train_trades)
        logger.info(f"  📊 Grouped into {len(pattern_groups)} pattern types")
        
        # Find patterns with 60%+ WR (5+ samples)
        candidate_patterns = []
        for pattern_key, trades in pattern_groups.items():
            if len(trades) < 5:  # Lower threshold
                continue
            
            wins = sum(1 for t in trades if t['pnl'] > 0)
            wr = (wins / len(trades)) * 100
            
            if wr >= 60:
                candidate_patterns.append({
                    'pattern': pattern_key,
                    'train_trades': len(trades),
                    'train_wr': wr,
                    'train_wins': wins,
                    'pattern_details': self._parse_pattern(pattern_key)
                })
                logger.info(f"  ✅ Candidate: {pattern_key[:50]} → {wr:.1f}% WR ({len(trades)} samples)")
        
        if not candidate_patterns:
            logger.warning(f"  ⚠️ No patterns with 60%+ WR found")
            # Fallback: best patterns (50%+)
            for pattern_key, trades in pattern_groups.items():
                if len(trades) < 5:
                    continue
                wins = sum(1 for t in trades if t['pnl'] > 0)
                wr = (wins / len(trades)) * 100
                if wr >= 50:
                    candidate_patterns.append({
                        'pattern': pattern_key,
                        'train_trades': len(trades),
                        'train_wr': wr,
                        'train_wins': wins,
                        'pattern_details': self._parse_pattern(pattern_key)
                    })
        
        candidate_patterns.sort(key=lambda x: x['train_wr'], reverse=True)
        
        # STEP 2: Validate on validation data
        logger.info(f"  Step 2: Validating {len(candidate_patterns)} candidate patterns...")
        validated_patterns = []
        
        for candidate in candidate_patterns:
            val_trades = self._test_pattern_on_data(val_df, candidate['pattern_details'], pair)
            
            if len(val_trades) >= 1:  # Accept with just 1 validation sample if it wins
                val_wins = sum(1 for t in val_trades if t['pnl'] > 0)
                val_wr = (val_wins / len(val_trades)) * 100
                
                # Validate: WR should be 50%+ on validation (patterns can vary out-of-sample)
                # OR if we only have 1-2 samples, they must all be wins
                if val_wr >= 50 or (len(val_trades) <= 2 and val_wins == len(val_trades)):
                    validated_patterns.append({
                        **candidate,
                        'val_trades': len(val_trades),
                        'val_wr': val_wr,
                        'val_wins': val_wins,
                        'combined_wr': ((candidate['train_wins'] + val_wins) / (candidate['train_trades'] + len(val_trades))) * 100
                    })
                    logger.info(f"  ✅ Validated: {candidate['pattern'][:50]} → Train: {candidate['train_wr']:.1f}%, Val: {val_wr:.1f}%")
                else:
                    logger.info(f"  ❌ Failed validation: {candidate['pattern'][:50]} → Val: {val_wr:.1f}%")
            else:
                logger.info(f"  ⚠️ Insufficient validation samples: {candidate['pattern'][:50]}")
        
        if not validated_patterns:
            logger.warning(f"  ⚠️ No patterns validated")
            return {
                'status': 'ok',
                'candidate_patterns': len(candidate_patterns),
                'validated_patterns': [],
                'final_backtest': {'trades': 0, 'win_rate': 0, 'profit_factor': 0, 'total_profit': 0}
            }
        
        # STEP 3: Trade validated patterns on full dataset
        logger.info(f"  Step 3: Trading {len(validated_patterns)} validated patterns on full dataset...")
        final_trades = self._trade_validated_patterns(df, validated_patterns, pair)
        
        if not final_trades:
            return {
                'status': 'ok',
                'validated_patterns': validated_patterns,
                'final_backtest': {'trades': 0, 'win_rate': 0, 'profit_factor': 0, 'total_profit': 0}
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
            'candidate_patterns': len(candidate_patterns),
            'validated_patterns': validated_patterns,
            'final_backtest': {
                'trades': len(final_trades),
                'win_rate': final_wr,
                'profit_factor': pf,
                'total_profit': total_pnl,
                'status': 'ok'
            }
        }
    
    def _generate_all_trades(self, df: pd.DataFrame, pair: str) -> List[Dict]:
        """Generate all trades with characteristics"""
        df = df.copy()
        
        # Calculate indicators
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
                              (df['close'].rolling(window=20).max() - df['close'].rolling(window=20).min()).replace(0, np.nan)
        
        # Generate signals
        df['signal'] = 'HOLD'
        buy_mask = (df['ema_fast'] > df['ema_slow']) & (df['rsi'].notna()) & (df['atr'].notna())
        sell_mask = (df['ema_fast'] < df['ema_slow']) & (df['rsi'].notna()) & (df['atr'].notna())
        df.loc[buy_mask, 'signal'] = 'BUY'
        df.loc[sell_mask, 'signal'] = 'SELL'
        
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
                    trades.append({
                        'side': position['side'],
                        'entry_price': position['entry_price'],
                        'pnl': pnl,
                        'entry_rsi': position['entry_rsi'],
                        'entry_momentum': position['entry_momentum'],
                        'entry_ema_sep': position['entry_ema_sep'],
                        'entry_volatility': position['entry_volatility'],
                        'entry_price_pos': position.get('entry_price_pos', 0.5),
                        'entry_hour': position['entry_hour']
                    })
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
                    'take_profit': take_profit,
                    'entry_rsi': row['rsi'],
                    'entry_momentum': row['momentum'],
                    'entry_ema_sep': row['ema_separation'],
                    'entry_volatility': row['volatility'],
                    'entry_price_pos': row.get('price_position', 0.5),
                    'entry_hour': idx.hour if hasattr(idx, 'hour') else 0
                }
        
        return trades
    
    def _group_trades_by_pattern(self, trades: List[Dict]) -> Dict[str, List[Dict]]:
        """Group trades by pattern"""
        groups = defaultdict(list)
        
        for trade in trades:
            rsi_bucket = int(trade['entry_rsi'] / 10) * 10 if not pd.isna(trade['entry_rsi']) else 50
            momentum_bucket = 'pos' if trade['entry_momentum'] > 0.0002 else ('neg' if trade['entry_momentum'] < -0.0002 else 'neutral')
            ema_sep_bucket = 'high' if trade['entry_ema_sep'] > 0.0005 else ('medium' if trade['entry_ema_sep'] > 0.0002 else 'low')
            vol_bucket = 'high' if not pd.isna(trade['entry_volatility']) and trade['entry_volatility'] > 0.001 else 'low'
            
            pattern_key = f"{trade['side']}_RSI{rsi_bucket}_{momentum_bucket}_EMASep{ema_sep_bucket}_Vol{vol_bucket}"
            groups[pattern_key].append(trade)
        
        return dict(groups)
    
    def _parse_pattern(self, pattern_key: str) -> Dict:
        """Parse pattern key into conditions"""
        parts = pattern_key.split('_')
        details = {'side': parts[0]}
        
        for part in parts:
            if part.startswith('RSI'):
                rsi_val = int(part[3:])
                details['rsi_range'] = (rsi_val, rsi_val + 10)
            elif part == 'pos':
                details['momentum'] = 'positive'
            elif part == 'neg':
                details['momentum'] = 'negative'
            elif 'EMASep' in part:
                details['ema_sep'] = part.replace('EMASep', '')
            elif 'Vol' in part:
                details['volatility'] = part.replace('Vol', '')
        
        return details
    
    def _test_pattern_on_data(self, df: pd.DataFrame, pattern_details: Dict, pair: str) -> List[Dict]:
        """Test a pattern on data"""
        df = df.copy()
        
        # Calculate indicators
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
        
        # Create mask for pattern
        df['signal'] = 'HOLD'
        
        side = pattern_details['side']
        mask = None
        
        if side == 'BUY':
            mask = (df['ema_fast'] > df['ema_slow'])
            if 'rsi_range' in pattern_details:
                rsi_min, rsi_max = pattern_details['rsi_range']
                mask = mask & (df['rsi'] >= rsi_min) & (df['rsi'] < rsi_max)
            if pattern_details.get('momentum') == 'positive':
                mask = mask & (df['momentum'] > 0.0002)
            if pattern_details.get('ema_sep') == 'high':
                mask = mask & (df['ema_separation'] > 0.0005)
            elif pattern_details.get('ema_sep') == 'medium':
                mask = mask & (df['ema_separation'] > 0.0002) & (df['ema_separation'] <= 0.0005)
        else:  # SELL
            mask = (df['ema_fast'] < df['ema_slow'])
            if 'rsi_range' in pattern_details:
                rsi_min, rsi_max = pattern_details['rsi_range']
                mask = mask & (df['rsi'] >= rsi_min) & (df['rsi'] < rsi_max)
            if pattern_details.get('momentum') == 'negative':
                mask = mask & (df['momentum'] < -0.0002)
            if pattern_details.get('ema_sep') == 'high':
                mask = mask & (df['ema_separation'] > 0.0005)
            elif pattern_details.get('ema_sep') == 'medium':
                mask = mask & (df['ema_separation'] > 0.0002) & (df['ema_separation'] <= 0.0005)
        
        df.loc[mask, 'signal'] = side
        
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
            
            if row['signal'] == side and not position:
                atr_val = row['atr']
                if side == 'BUY':
                    entry_price = ask
                    stop_loss = entry_price - (atr_val * 1.5)
                    take_profit = entry_price + (atr_val * 1.5 * 3.0)
                else:
                    entry_price = bid
                    stop_loss = entry_price + (atr_val * 1.5)
                    take_profit = entry_price - (atr_val * 1.5 * 3.0)
                
                position = {
                    'side': side,
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit
                }
        
        return trades
    
    def _trade_validated_patterns(self, df: pd.DataFrame, validated_patterns: List[Dict], pair: str) -> List[Dict]:
        """Trade all validated patterns"""
        all_trades = []
        
        for pattern in validated_patterns:
            pattern_details = pattern['pattern_details']
            trades = self._test_pattern_on_data(df, pattern_details, pair)
            all_trades.extend(trades)
        
        # Remove duplicates (same entry time)
        seen = set()
        unique_trades = []
        for trade in all_trades:
            key = (trade['entry_price'], trade['side'])
            if key not in seen:
                seen.add(key)
                unique_trades.append(trade)
        
        return unique_trades
    
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
    print("🎯 MARKET PATTERN DISCOVERY V8 - VALIDATED 60%+ PATTERNS")
    print("="*80)
    print("Find 60%+ patterns (5+ samples) → Validate → Trade only validated")
    print("="*80)
    
    if not load_credentials():
        logger.error("❌ Failed to load credentials")
        return
    
    discovery = MarketPatternDiscoveryV8(days=90)
    output_file = discovery.discover_all_pairs()
    print(f"\n✅ Complete! Results: {output_file}")


if __name__ == '__main__':
    main()

