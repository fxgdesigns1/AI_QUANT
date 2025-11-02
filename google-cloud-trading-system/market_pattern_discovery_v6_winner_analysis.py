#!/usr/bin/env python3
"""
Market Pattern Discovery V6 - Winner Analysis Approach
First: Generate many trades, analyze what makes winners win
Then: Only trade patterns that historically win 60%+
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

class MarketPatternDiscoveryV6:
    """V6: Learn from winners - analyze what makes trades win, then only trade those"""
    
    def __init__(self, days=60):  # More data = more samples
        self.days = days
        self.pairs = ['GBP_USD', 'XAU_USD', 'USD_JPY', 'EUR_USD', 'NZD_USD', 'AUD_USD']
        self.timeframes = ['M5', 'M15', 'H1']
        self.results = {}
        self.telegram = TelegramNotifier()
        
    def discover_all_pairs(self):
        """Discover patterns by learning from winners"""
        start_time = datetime.now()
        self._send_telegram(f"""🎓 <b>Pattern Discovery V6 - Winner Analysis</b>

📊 <b>{len(self.pairs)} pairs</b> | <b>{self.days} days</b>
🎯 Step 1: Generate trades → Analyze winners vs losers
🎯 Step 2: Identify 60%+ WR patterns → Trade only those
🕐 {start_time.strftime('%H:%M:%S')}""", message_type="v6_start")
        
        for idx, pair in enumerate(self.pairs, 1):
            pair_start = datetime.now()
            try:
                result = self.learn_from_winners(pair)
                self.results[pair] = result
                elapsed = (datetime.now() - pair_start).total_seconds() / 60
                self._send_pair_results(pair, result, idx, len(self.pairs), elapsed)
            except Exception as e:
                logger.error(f"❌ Error analyzing {pair}: {e}", exc_info=True)
                self.results[pair] = {'status': 'error', 'error': str(e)}
        
        total_time = (datetime.now() - start_time).total_seconds() / 60
        self._send_final_summary(total_time)
        
        output_file = f"pattern_discovery_v6_results_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        logger.info(f"✅ Results saved to: {output_file}")
        return output_file
    
    def _send_pair_results(self, pair: str, result: Dict, current: int, total: int, elapsed: float):
        """Send pair results"""
        if result.get('status') != 'ok':
            return
        
        backtest = result.get('backtest_results', {})
        trades = backtest.get('trades', 0)
        wr = backtest.get('win_rate', 0)
        
        status_icon = "🎯" if wr >= 60 else ("✅" if wr >= 50 else "⚠️")
        
        msg = f"""{status_icon} <b>{pair}</b> {wr:.1f}% WR

{trades} trades | {elapsed:.1f}min | {current}/{total}"""
        self._send_telegram(msg, message_type=f"pair_v6_{pair}")
    
    def _send_final_summary(self, total_minutes: float):
        """Send final summary"""
        msg = ["🎓 <b>Pattern Discovery V6 Complete</b>\n"]
        
        viable = 0
        total_trades = 0
        high_wr = []
        
        for pair, result in self.results.items():
            if result.get('status') == 'ok':
                backtest = result.get('backtest_results', {})
                trades = backtest.get('trades', 0)
                wr = backtest.get('win_rate', 0)
                
                if trades > 0:
                    viable += 1
                    total_trades += trades
                    if wr >= 60:
                        high_wr.append(f"{pair}: {wr:.1f}%")
                    msg.append(f"<b>{pair}:</b> {trades} trades | {wr:.1f}% WR")
        
        msg.append(f"\n✅ {viable}/6 viable | 📊 {total_trades} trades")
        if high_wr:
            msg.append(f"🎯 60%+ WR: {', '.join(high_wr)}")
        msg.append(f"⏱️ {total_minutes:.1f} min")
        
        self._send_telegram("\n".join(msg), message_type="v6_complete")
    
    def _send_telegram(self, message: str, message_type: str = "general"):
        """Send to Telegram"""
        try:
            self.telegram.send_message(message, message_type=message_type)
        except Exception as e:
            logger.warning(f"⚠️ Telegram failed: {e}")
    
    def learn_from_winners(self, pair: str) -> Dict:
        """Learn what makes trades win, then only trade those patterns"""
        logger.info(f"\n{'='*80}\n🎓 Learning from Winners: {pair}\n{'='*80}")
        
        client = OandaClient()
        primary_tf = 'M5'
        candles = get_historical_data(client, pair, days=self.days, granularity=primary_tf)
        
        if not candles or len(candles) < 200:
            return {'status': 'no_data'}
        
        df = self._candles_to_dataframe(candles)
        
        # STEP 1: Generate many trades with relaxed conditions to learn from
        logger.info("  Step 1: Generating trades to analyze...")
        all_trades = self._generate_all_trades(df, pair)
        
        if len(all_trades) < 50:
            logger.warning(f"  ⚠️ Only {len(all_trades)} trades - insufficient data")
            return {'status': 'insufficient_trades', 'trades': len(all_trades)}
        
        # STEP 2: Analyze winners vs losers
        logger.info(f"  Step 2: Analyzing {len(all_trades)} trades...")
        winners = [t for t in all_trades if t['pnl'] > 0]
        losers = [t for t in all_trades if t['pnl'] <= 0]
        
        win_rate = (len(winners) / len(all_trades)) * 100
        logger.info(f"  📊 Base WR: {win_rate:.1f}% ({len(winners)}/{len(all_trades)})")
        
        # STEP 3: Identify characteristics of winners
        winner_patterns = self._analyze_winner_characteristics(df, winners, losers)
        
        # STEP 4: Test only trading winner patterns
        logger.info("  Step 3: Testing winner-only patterns...")
        filtered_trades = self._filter_by_winner_patterns(df, winner_patterns, pair)
        
        if not filtered_trades:
            return {'status': 'no_filtered_trades', 'base_trades': len(all_trades), 'base_wr': win_rate}
        
        filtered_wr = (sum(1 for t in filtered_trades if t['pnl'] > 0) / len(filtered_trades)) * 100
        filtered_pnl = sum(t['pnl'] for t in filtered_trades)
        wins = [t for t in filtered_trades if t['pnl'] > 0]
        losses = [t for t in filtered_trades if t['pnl'] <= 0]
        gross_profit = sum(t['pnl'] for t in wins) if wins else 0
        gross_loss = abs(sum(t['pnl'] for t in losses)) if losses else 0
        pf = gross_profit / gross_loss if gross_loss > 0 else 0
        
        logger.info(f"  🎯 Filtered WR: {filtered_wr:.1f}% ({len(filtered_trades)} trades)")
        
        return {
            'status': 'ok',
            'base_trades': len(all_trades),
            'base_wr': win_rate,
            'filtered_trades': len(filtered_trades),
            'winner_patterns': winner_patterns,
            'backtest_results': {
                'trades': len(filtered_trades),
                'win_rate': filtered_wr,
                'profit_factor': pf,
                'total_profit': filtered_pnl,
                'status': 'ok'
            }
        }
    
    def _generate_all_trades(self, df: pd.DataFrame, pair: str) -> List[Dict]:
        """Generate trades with relaxed conditions to learn from"""
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
        
        # Generate signals (relaxed)
        df['signal'] = 'HOLD'
        buy_mask = (df['ema_fast'] > df['ema_slow']) & (df['rsi'] < 80) & (df['rsi'].notna()) & (df['atr'].notna())
        sell_mask = (df['ema_fast'] < df['ema_slow']) & (df['rsi'] > 20) & (df['rsi'].notna()) & (df['atr'].notna())
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
            
            # Store entry characteristics
            entry_rsi = row['rsi']
            entry_momentum = row['momentum']
            entry_ema_sep = row['ema_separation']
            
            # Close position
            if position:
                if (position['side'] == 'BUY' and row['signal'] == 'SELL') or \
                   (position['side'] == 'SELL' and row['signal'] == 'BUY'):
                    pnl = self._calculate_pnl(position, bid, ask, pair)
                    trades.append({
                        'side': position['side'],
                        'entry_price': position['entry_price'],
                        'entry_rsi': position['entry_rsi'],
                        'entry_momentum': position['entry_momentum'],
                        'entry_ema_sep': position['entry_ema_sep'],
                        'pnl': pnl,
                        'win': pnl > 0
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
                    'entry_rsi': entry_rsi,
                    'entry_momentum': entry_momentum,
                    'entry_ema_sep': entry_ema_sep
                }
        
        return trades
    
    def _analyze_winner_characteristics(self, df: pd.DataFrame, winners: List[Dict], losers: List[Dict]) -> Dict:
        """Analyze what makes winners different from losers"""
        if not winners or not losers:
            return {}
        
        # RSI analysis
        winner_rsi = [w['entry_rsi'] for w in winners if not pd.isna(w.get('entry_rsi'))]
        loser_rsi = [l['entry_rsi'] for l in losers if not pd.isna(l.get('entry_rsi'))]
        
        optimal_rsi_min = np.percentile(winner_rsi, 10) if winner_rsi else 30
        optimal_rsi_max = np.percentile(winner_rsi, 90) if winner_rsi else 70
        
        # Momentum analysis
        winner_momentum = [w['entry_momentum'] for w in winners if not pd.isna(w.get('entry_momentum'))]
        loser_momentum = [l['entry_momentum'] for l in losers if not pd.isna(l.get('entry_momentum'))]
        
        optimal_momentum_min = np.percentile(winner_momentum, 10) if winner_momentum else 0
        
        # EMA separation analysis
        winner_ema_sep = [w['entry_ema_sep'] for w in winners if not pd.isna(w.get('entry_ema_sep'))]
        loser_ema_sep = [l['entry_ema_sep'] for l in losers if not pd.isna(l.get('entry_ema_sep'))]
        
        optimal_ema_sep_min = np.percentile(winner_ema_sep, 10) if winner_ema_sep else 0.0001
        
        return {
            'rsi_range': (optimal_rsi_min, optimal_rsi_max),
            'momentum_min': optimal_momentum_min,
            'ema_separation_min': optimal_ema_sep_min
        }
    
    def _filter_by_winner_patterns(self, df: pd.DataFrame, patterns: Dict, pair: str) -> List[Dict]:
        """Only generate trades that match winner patterns"""
        if not patterns:
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
        
        rsi_min, rsi_max = patterns.get('rsi_range', (30, 70))
        momentum_min = patterns.get('momentum_min', 0)
        ema_sep_min = patterns.get('ema_separation_min', 0.0001)
        
        # Only trade winner patterns
        df['signal'] = 'HOLD'
        buy_mask = (
            (df['ema_fast'] > df['ema_slow']) &
            (df['rsi'] >= rsi_min) & (df['rsi'] <= rsi_max) &
            (df['momentum'] >= momentum_min) &
            (df['ema_separation'] >= ema_sep_min) &
            (df['rsi'].notna()) & (df['atr'].notna())
        )
        sell_mask = (
            (df['ema_fast'] < df['ema_slow']) &
            (df['rsi'] >= rsi_min) & (df['rsi'] <= rsi_max) &
            (df['momentum'] <= -momentum_min) &
            (df['ema_separation'] >= ema_sep_min) &
            (df['rsi'].notna()) & (df['atr'].notna())
        )
        df.loc[buy_mask, 'signal'] = 'BUY'
        df.loc[sell_mask, 'signal'] = 'SELL'
        
        # Backtest filtered signals
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
    print("🎓 MARKET PATTERN DISCOVERY V6 - WINNER ANALYSIS")
    print("="*80)
    print("Learn from winners → Trade only winning patterns")
    print("="*80)
    
    if not load_credentials():
        logger.error("❌ Failed to load credentials")
        return
    
    discovery = MarketPatternDiscoveryV6(days=60)
    output_file = discovery.discover_all_pairs()
    print(f"\n✅ Complete! Results: {output_file}")


if __name__ == '__main__':
    main()

