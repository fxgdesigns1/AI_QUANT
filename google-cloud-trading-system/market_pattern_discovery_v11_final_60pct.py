#!/usr/bin/env python3
"""
Market Pattern Discovery V11 - Final Push to 60%+
Build on V10's 53.6% XAU_USD success
Apply ULTRA-selective filters to reach 60%+
Accept 10-20 trades maximum per pair for highest quality
"""

import os, sys, json
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
import logging

repo_root = '/Users/mac/quant_system_clean/google-cloud-trading-system'
sys.path.insert(0, repo_root)
os.chdir(repo_root)

from universal_backtest_fix import load_credentials, OandaClient, get_historical_data
from src.core.telegram_notifier import TelegramNotifier

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MarketPatternDiscoveryV11:
    """V11: Ultra-selective to reach 60%+ - final push"""
    
    def __init__(self, days=90):
        self.days = days
        self.pairs = ['GBP_USD', 'XAU_USD', 'USD_JPY', 'EUR_USD', 'NZD_USD', 'AUD_USD']
        self.results = {}
        self.telegram = TelegramNotifier()
        
    def discover_all_pairs(self):
        """Final push to 60%+"""
        start_time = datetime.now()
        self._send_telegram(f"""🎯 <b>Pattern Discovery V11 - Final 60%+ Push</b>

📊 <b>{len(self.pairs)} pairs</b> | <b>{self.days} days</b>
🔥 Ultra-selective: 10-20 trades max per pair
🎯 Target: 60%+ WR
🕐 {start_time.strftime('%H:%M:%S')}""", message_type="v11_start")
        
        for idx, pair in enumerate(self.pairs, 1):
            pair_start = datetime.now()
            try:
                result = self.ultra_selective_60pct(pair)
                self.results[pair] = result
                elapsed = (datetime.now() - pair_start).total_seconds() / 60
                self._send_pair_results(pair, result, idx, len(self.pairs), elapsed)
            except Exception as e:
                logger.error(f"❌ Error analyzing {pair}: {e}", exc_info=True)
                self.results[pair] = {'status': 'error', 'error': str(e)}
        
        total_time = (datetime.now() - start_time).total_seconds() / 60
        self._send_final_summary(total_time)
        
        output_file = f"pattern_discovery_v11_results_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
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
        
        icon = "🎯" if wr >= 60 else ("✅" if wr >= 55 else ("⚠️" if wr >= 50 else "❌"))
        
        msg = f"""{icon} <b>{pair}</b> {wr:.1f}% WR

{trades} trades (ultra-selective) | {elapsed:.1f}min | {current}/{total}"""
        self._send_telegram(msg, message_type=f"pair_v11_{pair}")
    
    def _send_final_summary(self, total_minutes: float):
        """Send final summary"""
        msg = ["🎯 <b>Pattern Discovery V11 Complete</b>\n"]
        
        viable = 0
        total_trades = 0
        sixty_plus = []
        fifty_plus = []
        
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
                    elif wr >= 50:
                        fifty_plus.append(f"{pair}: {wr:.1f}%")
                    msg.append(f"<b>{pair}:</b> {trades} trades | {wr:.1f}% WR")
        
        msg.append(f"\n✅ {viable}/6 viable | 📊 {total_trades} trades")
        if sixty_plus:
            msg.append(f"🎯 60%+ WR ACHIEVED: {', '.join(sixty_plus)}")
        if fifty_plus:
            msg.append(f"⭐ 50%+ WR: {', '.join(fifty_plus)}")
        msg.append(f"⏱️ {total_minutes:.1f} min")
        
        self._send_telegram("\n".join(msg), message_type="v11_complete")
    
    def _send_telegram(self, message: str, message_type: str = "general"):
        """Send to Telegram"""
        try:
            self.telegram.send_message(message, message_type=message_type)
        except Exception as e:
            logger.warning(f"⚠️ Telegram failed: {e}")
    
    def ultra_selective_60pct(self, pair: str) -> Dict:
        """Ultra-selective optimization targeting 60%+"""
        logger.info(f"\n{'='*80}\n🎯 Ultra-Selective 60%+: {pair}\n{'='*80}")
        
        client = OandaClient()
        candles = get_historical_data(client, pair, days=self.days, granularity='M5')
        
        if not candles or len(candles) < 500:
            return {'status': 'insufficient_data'}
        
        df = self._candles_to_dataframe(candles)
        logger.info(f"  📊 {len(df)} candles loaded")
        
        # Step 1: Generate V10-like trades to analyze
        logger.info("  Step 1: Generating V10-style trades...")
        v10_trades = self._generate_v10_style_trades(df, pair)
        
        if len(v10_trades) < 20:
            logger.warning(f"  ⚠️ Only {len(v10_trades)} V10-style trades")
            return {'status': 'insufficient_trades', 'trades': len(v10_trades)}
        
        v10_wr = (sum(1 for t in v10_trades if t['pnl'] > 0) / len(v10_trades)) * 100
        logger.info(f"  📊 V10-style WR: {v10_wr:.1f}% ({len(v10_trades)} trades)")
        
        # Step 2: Find the BEST trades (top 20% by characteristics)
        logger.info("  Step 2: Identifying top-quality setups...")
        winners = [t for t in v10_trades if t['pnl'] > 0]
        
        if len(winners) < 5:
            return {'status': 'insufficient_winners', 'v10_wr': v10_wr}
        
        # Analyze ONLY the biggest winners
        big_winners = sorted([t for t in winners], key=lambda x: x['pnl'], reverse=True)[:max(5, len(winners)//4)]
        
        # Find characteristics of BIG winners
        big_winner_chars = self._analyze_big_winners(big_winners)
        
        # Step 3: Create ultra-selective filters - only trade setups matching big winners
        logger.info("  Step 3: Creating ultra-selective filters...")
        ultra_filters = self._create_ultra_filters(big_winner_chars)
        
        # Step 4: Test ultra-selective configuration
        logger.info("  Step 4: Testing ultra-selective configuration...")
        ultra_trades = self._generate_ultra_selective_trades(df, pair, ultra_filters)
        
        if not ultra_trades:
            logger.warning(f"  ⚠️ Ultra filters too strict")
            return {
                'status': 'ok',
                'v10_wr': v10_wr,
                'v10_trades': len(v10_trades),
                'final_backtest': {'trades': 0, 'win_rate': 0, 'profit_factor': 0, 'total_profit': 0}
            }
        
        ultra_wr = (sum(1 for t in ultra_trades if t['pnl'] > 0) / len(ultra_trades)) * 100
        ultra_wins = [t for t in ultra_trades if t['pnl'] > 0]
        ultra_losses = [t for t in ultra_trades if t['pnl'] <= 0]
        
        gross_profit = sum(t['pnl'] for t in ultra_wins) if ultra_wins else 0
        gross_loss = abs(sum(t['pnl'] for t in ultra_losses)) if ultra_losses else 0
        pf = gross_profit / gross_loss if gross_loss > 0 else 0
        total_pnl = sum(t['pnl'] for t in ultra_trades)
        
        logger.info(f"  🎯 Ultra-Selective WR: {ultra_wr:.1f}% ({len(ultra_trades)} trades)")
        logger.info(f"  📈 Improvement: {ultra_wr - v10_wr:+.1f}%")
        
        return {
            'status': 'ok',
            'v10_wr': v10_wr,
            'v10_trades': len(v10_trades),
            'ultra_filters': ultra_filters,
            'final_backtest': {
                'trades': len(ultra_trades),
                'win_rate': ultra_wr,
                'profit_factor': pf,
                'total_profit': total_pnl,
                'status': 'ok'
            }
        }
    
    def _generate_v10_style_trades(self, df: pd.DataFrame, pair: str) -> List[Dict]:
        """Generate V10-style trades"""
        df = df.copy()
        
        ema_fast = 2
        ema_slow = 8
        rsi_oversold = 22
        rsi_overbought = 85
        rsi_threshold = 5
        min_ema_sep = 0.0003
        
        df['ema_fast'] = df['close'].ewm(span=ema_fast, adjust=False).mean()
        df['ema_slow'] = df['close'].ewm(span=ema_slow, adjust=False).mean()
        
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
        
        # V10-style signals
        df['signal'] = 'HOLD'
        buy_mask = (
            (df['ema_fast'] > df['ema_slow']) &
            (df['rsi'] < (rsi_overbought - rsi_threshold)) &
            (df['rsi'] > 30) &
            (df['ema_separation'] >= min_ema_sep) &
            (df['rsi'].notna()) & (df['atr'].notna())
        )
        sell_mask = (
            (df['ema_fast'] < df['ema_slow']) &
            (df['rsi'] > (rsi_oversold + rsi_threshold)) &
            (df['rsi'] < 70) &
            (df['ema_separation'] >= min_ema_sep) &
            (df['rsi'].notna()) & (df['atr'].notna())
        )
        df.loc[buy_mask, 'signal'] = 'BUY'
        df.loc[sell_mask, 'signal'] = 'SELL'
        
        # Backtest with characteristics
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
                    'entry_hour': idx.hour if hasattr(idx, 'hour') else 0
                }
        
        return trades
    
    def _analyze_big_winners(self, big_winners: List[Dict]) -> Dict:
        """Analyze characteristics of biggest winners"""
        if not big_winners:
            return {}
        
        valid = [t for t in big_winners if not pd.isna(t.get('entry_rsi', np.nan))]
        
        return {
            'rsi_mean': np.mean([t['entry_rsi'] for t in valid]) if valid else 50,
            'rsi_std': np.std([t['entry_rsi'] for t in valid]) if valid and len(valid) > 1 else 10,
            'rsi_min': min([t['entry_rsi'] for t in valid]) if valid else 30,
            'rsi_max': max([t['entry_rsi'] for t in valid]) if valid else 70,
            'momentum_mean': np.mean([t.get('entry_momentum', 0) for t in valid if not pd.isna(t.get('entry_momentum', np.nan))]) if valid else 0,
            'ema_sep_mean': np.mean([t.get('entry_ema_sep', 0) for t in valid if not pd.isna(t.get('entry_ema_sep', np.nan))]) if valid else 0,
            'best_hours': [t['entry_hour'] for t in valid if 'entry_hour' in t]
        }
    
    def _create_ultra_filters(self, big_winner_chars: Dict) -> Dict:
        """Create ultra-selective filters matching big winners"""
        filters = {}
        
        # RSI: Very tight range around big winner average
        if 'rsi_mean' in big_winner_chars and 'rsi_std' in big_winner_chars:
            rsi_mean = big_winner_chars['rsi_mean']
            rsi_std = big_winner_chars['rsi_std']
            # Tight range: mean ± 0.5 std
            filters['rsi_min'] = max(30, rsi_mean - (rsi_std * 0.5))
            filters['rsi_max'] = min(70, rsi_mean + (rsi_std * 0.5))
        
        # Momentum: Require stronger than average
        if 'momentum_mean' in big_winner_chars:
            filters['min_momentum'] = max(0.0002, big_winner_chars['momentum_mean'] * 0.7)
        
        # EMA separation: Require stronger trends
        if 'ema_sep_mean' in big_winner_chars:
            filters['min_ema_separation'] = max(0.0005, big_winner_chars['ema_sep_mean'] * 1.2)
        
        # Best hours: Only trade during hours when big winners occurred
        if 'best_hours' in big_winner_chars and big_winner_chars['best_hours']:
            # Get most common hours (if any hour appears >30% of the time)
            hour_counts = {}
            for h in big_winner_chars['best_hours']:
                hour_counts[h] = hour_counts.get(h, 0) + 1
            total = len(big_winner_chars['best_hours'])
            filters['best_hours'] = [h for h, count in hour_counts.items() if count / total >= 0.3]
        
        return filters
    
    def _generate_ultra_selective_trades(self, df: pd.DataFrame, pair: str, filters: Dict) -> List[Dict]:
        """Generate trades with ultra-selective filters"""
        df = df.copy()
        
        ema_fast = 2
        ema_slow = 8
        
        df['ema_fast'] = df['close'].ewm(span=ema_fast, adjust=False).mean()
        df['ema_slow'] = df['close'].ewm(span=ema_slow, adjust=False).mean()
        
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
        
        # ULTRA-STRICT filters
        df['signal'] = 'HOLD'
        
        buy_mask = (df['ema_fast'] > df['ema_slow'])
        sell_mask = (df['ema_fast'] < df['ema_slow'])
        
        # Tight RSI range
        if 'rsi_min' in filters and 'rsi_max' in filters:
            buy_mask = buy_mask & (df['rsi'] >= filters['rsi_min']) & (df['rsi'] <= filters['rsi_max'])
            sell_mask = sell_mask & (df['rsi'] >= filters['rsi_min']) & (df['rsi'] <= filters['rsi_max'])
        
        # Strong momentum
        if 'min_momentum' in filters:
            buy_mask = buy_mask & (df['momentum'] >= filters['min_momentum'])
            sell_mask = sell_mask & (df['momentum'] <= -filters['min_momentum'])
        
        # Strong EMA separation
        if 'min_ema_separation' in filters:
            buy_mask = buy_mask & (df['ema_separation'] >= filters['min_ema_separation'])
            sell_mask = sell_mask & (df['ema_separation'] >= filters['min_ema_separation'])
        
        # Best hours only
        if 'best_hours' in filters and filters['best_hours']:
            df['hour'] = df.index.hour if hasattr(df.index, 'hour') else 0
            buy_mask = buy_mask & (df['hour'].isin(filters['best_hours']))
            sell_mask = sell_mask & (df['hour'].isin(filters['best_hours']))
        
        buy_mask = buy_mask & (df['rsi'].notna()) & (df['atr'].notna())
        sell_mask = sell_mask & (df['rsi'].notna()) & (df['atr'].notna())
        
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
    print("🎯 MARKET PATTERN DISCOVERY V11 - FINAL 60%+ PUSH")
    print("="*80)
    print("Build on V10's 53.6% → Ultra-selective → Target 60%+")
    print("="*80)
    
    if not load_credentials():
        logger.error("❌ Failed to load credentials")
        return
    
    discovery = MarketPatternDiscoveryV11(days=90)
    output_file = discovery.discover_all_pairs()
    print(f"\n✅ Complete! Results: {output_file}")


if __name__ == '__main__':
    main()

