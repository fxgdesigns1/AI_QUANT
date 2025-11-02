#!/usr/bin/env python3
"""
Market Pattern Discovery V10 - Refined Approach
Build on V4's 47.6% success → Analyze winners vs losers → Add selective filters → Target 60%+
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

class MarketPatternDiscoveryV10:
    """V10: Analyze V4 winners/losers, add selective filters to reach 60%+"""
    
    def __init__(self, days=90):
        self.days = days
        self.pairs = ['GBP_USD', 'XAU_USD', 'USD_JPY', 'EUR_USD', 'NZD_USD', 'AUD_USD']
        self.results = {}
        self.telegram = TelegramNotifier()
        
    def discover_all_pairs(self):
        """Refined discovery targeting 60%+"""
        start_time = datetime.now()
        self._send_telegram(f"""🎯 <b>Pattern Discovery V10 - Refined 60%+</b>

📊 <b>{len(self.pairs)} pairs</b> | <b>{self.days} days</b>
🔍 Analyze V4 winners → Eliminate losers → Target 60%+
🕐 {start_time.strftime('%H:%M:%S')}""", message_type="v10_start")
        
        for idx, pair in enumerate(self.pairs, 1):
            pair_start = datetime.now()
            try:
                result = self.refined_optimization(pair)
                self.results[pair] = result
                elapsed = (datetime.now() - pair_start).total_seconds() / 60
                self._send_pair_results(pair, result, idx, len(self.pairs), elapsed)
            except Exception as e:
                logger.error(f"❌ Error analyzing {pair}: {e}", exc_info=True)
                self.results[pair] = {'status': 'error', 'error': str(e)}
        
        total_time = (datetime.now() - start_time).total_seconds() / 60
        self._send_final_summary(total_time)
        
        output_file = f"pattern_discovery_v10_results_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
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

{trades} trades | {elapsed:.1f}min | {current}/{total}"""
        self._send_telegram(msg, message_type=f"pair_v10_{pair}")
    
    def _send_final_summary(self, total_minutes: float):
        """Send final summary"""
        msg = ["🎯 <b>Pattern Discovery V10 Complete</b>\n"]
        
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
        
        self._send_telegram("\n".join(msg), message_type="v10_complete")
    
    def _send_telegram(self, message: str, message_type: str = "general"):
        """Send to Telegram"""
        try:
            self.telegram.send_message(message, message_type=message_type)
        except Exception as e:
            logger.warning(f"⚠️ Telegram failed: {e}")
    
    def refined_optimization(self, pair: str) -> Dict:
        """Refined optimization: analyze V4 pattern, eliminate losers"""
        logger.info(f"\n{'='*80}\n🎯 Refined Optimization: {pair}\n{'='*80}")
        
        client = OandaClient()
        candles = get_historical_data(client, pair, days=self.days, granularity='M5')
        
        if not candles or len(candles) < 500:
            return {'status': 'insufficient_data'}
        
        df = self._candles_to_dataframe(candles)
        logger.info(f"  📊 {len(df)} candles loaded")
        
        # Step 1: Generate trades with V4-like config (baseline)
        logger.info("  Step 1: Generating baseline trades (V4-like config)...")
        baseline_trades = self._generate_baseline_trades(df, pair)
        
        if len(baseline_trades) < 30:
            logger.warning(f"  ⚠️ Only {len(baseline_trades)} baseline trades")
            return {'status': 'insufficient_trades', 'trades': len(baseline_trades)}
        
        baseline_wr = (sum(1 for t in baseline_trades if t['pnl'] > 0) / len(baseline_trades)) * 100
        logger.info(f"  📊 Baseline WR: {baseline_wr:.1f}% ({len(baseline_trades)} trades)")
        
        # Step 2: Analyze winners vs losers
        logger.info("  Step 2: Analyzing winners vs losers...")
        winners = [t for t in baseline_trades if t['pnl'] > 0]
        losers = [t for t in baseline_trades if t['pnl'] <= 0]
        
        if len(winners) < 5 or len(losers) < 5:
            logger.warning(f"  ⚠️ Insufficient winners/losers for analysis")
            return {'status': 'insufficient_samples', 'baseline_wr': baseline_wr}
        
        # Find characteristics that differentiate winners from losers
        winner_characteristics = self._analyze_characteristics(winners)
        loser_characteristics = self._analyze_characteristics(losers)
        
        # Step 3: Create refined filters based on analysis
        logger.info("  Step 3: Creating refined filters...")
        refined_filters = self._create_refined_filters(winner_characteristics, loser_characteristics)
        
        # Step 4: Test refined configuration
        logger.info("  Step 4: Testing refined configuration...")
        refined_trades = self._generate_refined_trades(df, pair, refined_filters)
        
        if not refined_trades:
            logger.warning(f"  ⚠️ Refined filters too strict - no trades")
            return {
                'status': 'ok',
                'baseline_wr': baseline_wr,
                'baseline_trades': len(baseline_trades),
                'refined_filters': refined_filters,
                'final_backtest': {'trades': 0, 'win_rate': 0, 'profit_factor': 0, 'total_profit': 0}
            }
        
        refined_wr = (sum(1 for t in refined_trades if t['pnl'] > 0) / len(refined_trades)) * 100
        refined_wins = [t for t in refined_trades if t['pnl'] > 0]
        refined_losses = [t for t in refined_trades if t['pnl'] <= 0]
        
        gross_profit = sum(t['pnl'] for t in refined_wins) if refined_wins else 0
        gross_loss = abs(sum(t['pnl'] for t in refined_losses)) if refined_losses else 0
        pf = gross_profit / gross_loss if gross_loss > 0 else 0
        total_pnl = sum(t['pnl'] for t in refined_trades)
        
        logger.info(f"  🎯 Refined WR: {refined_wr:.1f}% ({len(refined_trades)} trades)")
        logger.info(f"  📈 Improvement: {refined_wr - baseline_wr:+.1f}%")
        
        return {
            'status': 'ok',
            'baseline_wr': baseline_wr,
            'baseline_trades': len(baseline_trades),
            'refined_filters': refined_filters,
            'final_backtest': {
                'trades': len(refined_trades),
                'win_rate': refined_wr,
                'profit_factor': pf,
                'total_profit': total_pnl,
                'status': 'ok'
            }
        }
    
    def _generate_baseline_trades(self, df: pd.DataFrame, pair: str) -> List[Dict]:
        """Generate trades with V4-like baseline configuration"""
        df = df.copy()
        
        # V4 baseline config (from XAU_USD 47.6% success)
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
        df['price_position'] = (df['close'] - df['close'].rolling(window=20).min()) / \
                              (df['close'].rolling(window=20).max() - df['close'].rolling(window=20).min()).replace(0, np.nan)
        
        # Generate signals (V4-like)
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
        
        # Backtest and capture characteristics
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
    
    def _analyze_characteristics(self, trades: List[Dict]) -> Dict:
        """Analyze characteristics of trades"""
        if not trades:
            return {}
        
        valid_trades = [t for t in trades if not pd.isna(t.get('entry_rsi', np.nan))]
        
        return {
            'rsi_median': np.median([t['entry_rsi'] for t in valid_trades]) if valid_trades else 50,
            'rsi_q25': np.percentile([t['entry_rsi'] for t in valid_trades], 25) if valid_trades else 30,
            'rsi_q75': np.percentile([t['entry_rsi'] for t in valid_trades], 75) if valid_trades else 70,
            'momentum_median': np.median([t.get('entry_momentum', 0) for t in valid_trades if not pd.isna(t.get('entry_momentum', np.nan))]) if valid_trades else 0,
            'ema_sep_median': np.median([t.get('entry_ema_sep', 0) for t in valid_trades if not pd.isna(t.get('entry_ema_sep', np.nan))]) if valid_trades else 0,
            'volatility_median': np.median([t.get('entry_volatility', 0) for t in valid_trades if not pd.isna(t.get('entry_volatility', np.nan))]) if valid_trades else 0,
        }
    
    def _create_refined_filters(self, winners: Dict, losers: Dict) -> Dict:
        """Create filters that favor winners and eliminate losers"""
        filters = {}
        
        # RSI filters - favor winner ranges, avoid loser ranges
        if winners.get('rsi_q25') and losers.get('rsi_q25'):
            # Winners tend to be in a specific RSI range
            filters['rsi_min'] = max(winners['rsi_q25'] - 5, 25)
            filters['rsi_max'] = min(winners['rsi_q75'] + 5, 75)
            
            # Avoid loser RSI ranges
            filters['avoid_rsi_low'] = losers.get('rsi_q25', 0)
            filters['avoid_rsi_high'] = losers.get('rsi_q75', 100)
        
        # Momentum - require positive for winners
        if winners.get('momentum_median', 0) > 0:
            filters['min_momentum'] = max(0, winners['momentum_median'] * 0.5)
        
        # EMA separation - require stronger trends
        if winners.get('ema_sep_median', 0) > losers.get('ema_sep_median', 0):
            filters['min_ema_separation'] = max(0.0003, winners['ema_sep_median'] * 0.8)
        
        return filters
    
    def _generate_refined_trades(self, df: pd.DataFrame, pair: str, filters: Dict) -> List[Dict]:
        """Generate trades with refined filters"""
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
        
        # Apply refined filters
        df['signal'] = 'HOLD'
        
        buy_mask = (df['ema_fast'] > df['ema_slow'])
        sell_mask = (df['ema_fast'] < df['ema_slow'])
        
        # RSI filters
        if 'rsi_min' in filters and 'rsi_max' in filters:
            buy_mask = buy_mask & (df['rsi'] >= filters['rsi_min']) & (df['rsi'] <= filters['rsi_max'])
            sell_mask = sell_mask & (df['rsi'] >= filters['rsi_min']) & (df['rsi'] <= filters['rsi_max'])
        
        # Avoid loser RSI ranges
        if 'avoid_rsi_low' in filters and 'avoid_rsi_high' in filters:
            buy_mask = buy_mask & ~((df['rsi'] >= filters['avoid_rsi_low']) & (df['rsi'] <= filters['avoid_rsi_high']))
            sell_mask = sell_mask & ~((df['rsi'] >= filters['avoid_rsi_low']) & (df['rsi'] <= filters['avoid_rsi_high']))
        
        # Momentum filter
        if 'min_momentum' in filters:
            buy_mask = buy_mask & (df['momentum'] >= filters['min_momentum'])
            sell_mask = sell_mask & (df['momentum'] <= -filters['min_momentum'])
        
        # EMA separation filter
        if 'min_ema_separation' in filters:
            buy_mask = buy_mask & (df['ema_separation'] >= filters['min_ema_separation'])
            sell_mask = sell_mask & (df['ema_separation'] >= filters['min_ema_separation'])
        
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
    print("🎯 MARKET PATTERN DISCOVERY V10 - REFINED 60%+")
    print("="*80)
    print("Analyze V4 winners → Eliminate losers → Target 60%+")
    print("="*80)
    
    if not load_credentials():
        logger.error("❌ Failed to load credentials")
        return
    
    discovery = MarketPatternDiscoveryV10(days=90)
    output_file = discovery.discover_all_pairs()
    print(f"\n✅ Complete! Results: {output_file}")


if __name__ == '__main__':
    main()

