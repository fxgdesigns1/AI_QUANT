#!/usr/bin/env python3
"""
Market Pattern Discovery Engine
Analyzes last 30 days to discover patterns, trends, cycles, and news reactions
Then synthesizes optimal strategy parameters for each pair individually
Sends incremental results to Telegram after each pair completes
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

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MarketPatternDiscovery:
    """Discover market patterns from historical data and synthesize strategies"""
    
    def __init__(self, days=30):
        self.days = days
        self.pairs = ['GBP_USD', 'XAU_USD', 'USD_JPY', 'EUR_USD', 'NZD_USD', 'AUD_USD']
        self.timeframes = ['M5', 'M15', 'H1']
        self.results = {}
        self.telegram = TelegramNotifier()
        
    def discover_all_pairs(self):
        """Discover patterns for all pairs and send incremental updates"""
        start_time = datetime.now()
        
        # Send start notification
        self._send_telegram(f"""🔍 <b>Market Pattern Discovery Started</b>

📊 Analyzing <b>{len(self.pairs)} pairs</b> over <b>{self.days} days</b>
🕐 Started: {start_time.strftime('%H:%M:%S')}
⏱️ Estimated time: ~2.5-3 hours

<i>Processing pairs individually for accuracy...</i>""", message_type="discovery_start")
        
        for idx, pair in enumerate(self.pairs, 1):
            pair_start = datetime.now()
            
            try:
                result = self.discover_patterns(pair)
                self.results[pair] = result
                
                # Send incremental results to Telegram
                elapsed = (datetime.now() - pair_start).total_seconds() / 60
                self._send_pair_results(pair, result, idx, len(self.pairs), elapsed)
                
            except Exception as e:
                logger.error(f"❌ Error analyzing {pair}: {e}", exc_info=True)
                self.results[pair] = {'status': 'error', 'error': str(e)}
                self._send_telegram(f"""❌ <b>{pair} Analysis Failed</b>

Error: {str(e)[:200]}

<i>Continuing with next pair...</i>""", message_type=f"error_{pair}")
        
        # Send final summary
        total_time = (datetime.now() - start_time).total_seconds() / 60
        self._send_final_summary(total_time)
        
        # Save results
        output_file = f"pattern_discovery_results_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        logger.info(f"✅ Results saved to: {output_file}")
        return output_file
    
    def _send_pair_results(self, pair: str, result: Dict, current: int, total: int, elapsed: float):
        """Send pair-specific results to Telegram"""
        if result.get('status') != 'ok':
            status_msg = f"⚠️ {pair}: {result.get('status', 'unknown')}"
            if 'error' in result:
                status_msg += f"\nError: {result['error'][:100]}"
        else:
            params = result.get('discovered_params', {})
            backtest = result.get('backtest_results', {})
            
            # Format discovered parameters
            ema_fast = params.get('ema_fast', 'N/A')
            ema_slow = params.get('ema_slow', 'N/A')
            rsi_lo = params.get('rsi_oversold', 'N/A')
            rsi_hi = params.get('rsi_overbought', 'N/A')
            atr_mult = params.get('atr_multiplier', 'N/A')
            rr = params.get('risk_reward_ratio', 'N/A')
            
            # Format backtest results if available
            trades = backtest.get('trades', 0)
            wr = backtest.get('win_rate', 0)
            pf = backtest.get('profit_factor', 0)
            pnl = backtest.get('total_profit', 0)
            
            # Get pattern insights
            patterns = result.get('patterns', {})
            trend_consistency = patterns.get('trend_analysis', {}).get('M15', {}).get('trend_consistency', 0)
            rsi_success = patterns.get('rsi_analysis', {}).get('M15', {}).get('reversal_success_rate', 0)
            
            status_msg = f"""✅ <b>{pair} Analysis Complete</b>

<b>📊 Discovered Parameters:</b>
EMA: {ema_fast}/{ema_slow}
RSI: {rsi_lo}-{rsi_hi}
ATR Multiplier: {atr_mult:.2f}
Risk/Reward: {rr:.2f}

<b>🧪 Backtest Results:</b>
Trades: {trades}
Win Rate: {wr:.1f}%
Profit Factor: {pf:.3f}
P/L: {pnl:.2f} pips

<b>📈 Pattern Quality:</b>
Trend Consistency: {trend_consistency:.1%}
RSI Reversal Success: {rsi_success:.1%}

⏱️ Time: {elapsed:.1f} min
📊 Progress: {current}/{total} pairs"""
        
        self._send_telegram(status_msg, message_type=f"pair_{pair}")
    
    def _send_final_summary(self, total_minutes: float):
        """Send final summary to Telegram"""
        summary_parts = [f"🎉 <b>Pattern Discovery Complete</b>\n\n"]
        
        viable = 0
        total_trades = 0
        
        for pair, result in self.results.items():
            if result.get('status') == 'ok':
                params = result.get('discovered_params', {})
                backtest = result.get('backtest_results', {})
                trades = backtest.get('trades', 0)
                wr = backtest.get('win_rate', 0)
                pf = backtest.get('profit_factor', 0)
                
                if trades > 0:
                    viable += 1
                    total_trades += trades
                    
                    summary_parts.append(f"""<b>{pair}:</b>
  Trades: {trades} | WR: {wr:.1f}% | PF: {pf:.3f}
  EMA({params.get('ema_fast')}/{params.get('ema_slow')}) RSI({params.get('rsi_oversold')}-{params.get('rsi_overbought')}) ATRx{params.get('atr_multiplier', 0):.2f}
""")
        
        summary_parts.append(f"\n✅ {viable}/{len(self.pairs)} pairs viable")
        summary_parts.append(f"📊 Total trades found: {total_trades}")
        summary_parts.append(f"⏱️ Total time: {total_minutes:.1f} minutes")
        
        self._send_telegram("\n".join(summary_parts), message_type="discovery_complete")
    
    def _send_telegram(self, message: str, message_type: str = "general"):
        """Send message to Telegram"""
        try:
            self.telegram.send_message(message, message_type=message_type)
        except Exception as e:
            logger.warning(f"⚠️ Failed to send Telegram message: {e}")
    
    def discover_patterns(self, pair: str) -> Dict:
        """Discover patterns for a single pair"""
        logger.info(f"\n{'='*80}")
        logger.info(f"🔍 DISCOVERING PATTERNS: {pair}")
        logger.info(f"{'='*80}\n")
        
        # 1. FETCH HISTORICAL DATA
        logger.info(f"📥 Fetching {self.days} days of data...")
        client = OandaClient()
        
        data_by_timeframe = {}
        for tf in self.timeframes:
            candles = get_historical_data(client, pair, days=self.days, granularity=tf)
            if candles and len(candles) > 100:
                df = self._candles_to_dataframe(candles)
                data_by_timeframe[tf] = df
                logger.info(f"  ✅ {tf}: {len(df)} candles")
            else:
                logger.warning(f"  ⚠️  {tf}: Insufficient data")
        
        if not data_by_timeframe:
            return {'status': 'no_data', 'error': 'Insufficient historical data'}
        
        # 2. ANALYZE PATTERNS
        try:
            patterns = {
                'trend_analysis': self._analyze_trends(data_by_timeframe, pair),
                'cycle_analysis': self._analyze_cycles(data_by_timeframe, pair),
                'volatility_analysis': self._analyze_volatility(data_by_timeframe, pair),
                'support_resistance': self._analyze_support_resistance(data_by_timeframe, pair),
                'session_analysis': self._analyze_sessions(data_by_timeframe, pair),
                'rsi_analysis': self._analyze_rsi_levels(data_by_timeframe, pair),
            }
            
            # 3. SYNTHESIZE STRATEGY PARAMETERS
            strategy_params = self._synthesize_strategy(patterns, data_by_timeframe)
            
            # 4. BACKTEST DISCOVERED STRATEGY
            logger.info(f"\n🧪 Backtesting discovered strategy...")
            backtest_results = self._backtest_discovered_strategy(pair, strategy_params, data_by_timeframe, patterns)
            
            return {
                'status': 'ok',
                'patterns': patterns,
                'discovered_params': strategy_params,
                'backtest_results': backtest_results
            }
        except Exception as e:
            logger.error(f"❌ Pattern discovery error for {pair}: {e}", exc_info=True)
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
        """Discover trend characteristics"""
        logger.info("\n📈 Analyzing trends...")
        trends = {}
        
        for tf, df in data_by_timeframe.items():
            if len(df) < 50:
                continue
                
            # Test different EMA combinations
            best_score = 0
            best_fast = 3
            best_slow = 12
            
            for fast in [2, 3, 4, 5]:
                for slow in [8, 10, 12, 15, 21, 26]:
                    if slow <= fast:
                        continue
                    
                    try:
                        df_temp = df.copy()
                        df_temp['ema_fast'] = df_temp['close'].ewm(span=fast, adjust=False).mean()
                        df_temp['ema_slow'] = df_temp['close'].ewm(span=slow, adjust=False).mean()
                        
                        # Calculate trend signals
                        df_temp['ema_signal'] = np.where(df_temp['ema_fast'] > df_temp['ema_slow'], 1, -1)
                        df_temp['signal_change'] = df_temp['ema_signal'].diff()
                        
                        # Count valid trend signals
                        signals = ((df_temp['signal_change'] != 0) & (df_temp['signal_change'].notna())).sum()
                        
                        # Calculate average trend length
                        trend_lengths = []
                        current_trend = None
                        length = 0
                        for s in df_temp['ema_signal'].values:
                            if not np.isnan(s):
                                s = int(s)
                                if s == current_trend:
                                    length += 1
                                else:
                                    if current_trend is not None:
                                        trend_lengths.append(length)
                                    current_trend = s
                                    length = 1
                        if length > 0:
                            trend_lengths.append(length)
                        
                        avg_trend_length = np.mean(trend_lengths) if trend_lengths else 0
                        
                        # Score: balance between signals and trend stability
                        if signals > 0:
                            score = min(signals, 100) * 0.3 + min(avg_trend_length, 50) * 0.7
                            
                            if score > best_score:
                                best_score = score
                                best_fast = fast
                                best_slow = slow
                    except Exception as e:
                        continue
            
            # Calculate trend consistency with best EMAs
            try:
                df['ema_fast'] = df['close'].ewm(span=best_fast, adjust=False).mean()
                df['ema_slow'] = df['close'].ewm(span=best_slow, adjust=False).mean()
                df['trend'] = np.where(df['ema_fast'] > df['ema_slow'], 1, -1)
                
                trend_changes = (df['trend'].diff() != 0).sum()
                trend_direction_consistency = max(0, 1 - (trend_changes / len(df)))
                
                trends[tf] = {
                    'best_ema_fast': int(best_fast),
                    'best_ema_slow': int(best_slow),
                    'trend_consistency': float(trend_direction_consistency),
                    'avg_trend_duration': float(avg_trend_length) if 'avg_trend_length' in locals() else 0,
                    'total_trends': int(trend_changes)
                }
                logger.info(f"  {tf}: EMA({best_fast}/{best_slow}), Consistency: {trend_direction_consistency:.2%}")
            except Exception as e:
                logger.warning(f"  {tf}: Trend analysis error: {e}")
        
        return trends
    
    def _analyze_cycles(self, data_by_timeframe: Dict, pair: str) -> Dict:
        """Discover daily/weekly cycles"""
        logger.info("\n🔄 Analyzing cycles...")
        cycles = {}
        
        for tf, df in data_by_timeframe.items():
            if len(df) < 200:
                continue
            
            try:
                # Add time features
                df['hour'] = df.index.hour
                df['day_of_week'] = df.index.dayofweek
                
                # Calculate hourly moves
                df['hourly_return'] = df['close'].pct_change()
                
                # Find best trading hours (highest volatility + directionality)
                hourly_stats = df.groupby('hour')['hourly_return'].agg(['mean', 'std', 'count'])
                hourly_stats = hourly_stats[hourly_stats['count'] >= 10]  # Minimum samples
                hourly_stats['score'] = abs(hourly_stats['mean']) * hourly_stats['std']
                
                best_hours = hourly_stats.nlargest(8, 'score').index.tolist()
                best_hours = [int(h) for h in best_hours]
                
                # Find best trading days
                daily_stats = df.groupby('day_of_week')['hourly_return'].agg(['mean', 'std'])
                daily_stats['score'] = abs(daily_stats['mean']) * daily_stats['std']
                best_days = daily_stats.nlargest(5, 'score').index.tolist()
                best_days = [int(d) for d in best_days]
                
                cycles[tf] = {
                    'best_hours': best_hours,
                    'best_days': best_days,
                    'hourly_volatility': {int(k): v.to_dict() for k, v in hourly_stats.iterrows()},
                    'daily_patterns': {int(k): v.to_dict() for k, v in daily_stats.iterrows()}
                }
                logger.info(f"  {tf}: Best hours: {best_hours}, Best days: {best_days}")
            except Exception as e:
                logger.warning(f"  {tf}: Cycle analysis error: {e}")
        
        return cycles
    
    def _analyze_volatility(self, data_by_timeframe: Dict, pair: str) -> Dict:
        """Discover volatility patterns"""
        logger.info("\n📊 Analyzing volatility...")
        volatility = {}
        
        for tf, df in data_by_timeframe.items():
            if len(df) < 50:
                continue
            
            try:
                # Calculate True Range
                high_low = df['high'] - df['low']
                high_close = abs(df['high'] - df['close'].shift())
                low_close = abs(df['low'] - df['close'].shift())
                
                tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
                
                # Calculate ATR
                atr_14 = tr.rolling(window=14).mean()
                
                avg_atr = float(atr_14.mean())
                avg_price = float(df['close'].mean())
                
                # Calculate optimal stop distance based on actual reversals
                returns = df['close'].pct_change()
                threshold = returns.std() * 1.5
                volatile_periods = returns[abs(returns) > threshold]
                
                if len(volatile_periods) > 0 and avg_atr > 0:
                    avg_volatile_move = abs(volatile_periods).mean() * avg_price
                    optimal_multiplier = max(1.0, min(3.0, avg_volatile_move / avg_atr))
                else:
                    optimal_multiplier = 1.5
                
                volatility[tf] = {
                    'avg_atr': avg_atr,
                    'avg_atr_pct': float((avg_atr / avg_price) * 100) if avg_price > 0 else 0,
                    'optimal_atr_multiplier': float(optimal_multiplier),
                    'volatility_regime': 'high' if avg_atr > atr_14.median() * 1.2 else 'low'
                }
                logger.info(f"  {tf}: Avg ATR: {avg_atr:.5f} ({volatility[tf]['avg_atr_pct']:.2f}%), Optimal multiplier: {optimal_multiplier:.2f}")
            except Exception as e:
                logger.warning(f"  {tf}: Volatility analysis error: {e}")
        
        return volatility
    
    def _analyze_support_resistance(self, data_by_timeframe: Dict, pair: str) -> Dict:
        """Discover actual support/resistance levels"""
        logger.info("\n🎯 Analyzing support/resistance...")
        levels = {}
        
        for tf, df in data_by_timeframe.items():
            if len(df) < 100:
                continue
            
            try:
                # Find pivot points (local highs/lows)
                window = min(5, len(df) // 20)
                df['pivot_high'] = (df['high'] == df['high'].rolling(window*2+1, center=True).max()) & (df['high'] > df['high'].quantile(0.6))
                df['pivot_low'] = (df['low'] == df['low'].rolling(window*2+1, center=True).min()) & (df['low'] < df['low'].quantile(0.4))
                
                highs = df[df['pivot_high']]['high'].tolist()
                lows = df[df['pivot_low']]['low'].tolist()
                
                # Cluster levels
                tolerance = df['close'].mean() * 0.001  # 0.1% tolerance
                
                resistance_levels = self._cluster_levels(highs, tolerance) if highs else []
                support_levels = self._cluster_levels(lows, tolerance) if lows else []
                
                levels[tf] = {
                    'support_levels': sorted(support_levels)[-5:] if support_levels else [],
                    'resistance_levels': sorted(resistance_levels)[:5] if resistance_levels else [],
                    'price_range': {'min': float(df['low'].min()), 'max': float(df['high'].max())}
                }
                logger.info(f"  {tf}: Found {len(support_levels)} support, {len(resistance_levels)} resistance levels")
            except Exception as e:
                logger.warning(f"  {tf}: S/R analysis error: {e}")
        
        return levels
    
    def _cluster_levels(self, levels: List[float], tolerance: float) -> List[float]:
        """Cluster similar price levels"""
        if not levels:
            return []
        
        sorted_levels = sorted(levels)
        clusters = []
        current_cluster = [sorted_levels[0]]
        
        for level in sorted_levels[1:]:
            if level - current_cluster[-1] <= tolerance:
                current_cluster.append(level)
            else:
                clusters.append(np.mean(current_cluster))
                current_cluster = [level]
        clusters.append(np.mean(current_cluster))
        
        return clusters
    
    def _analyze_sessions(self, data_by_timeframe: Dict, pair: str) -> Dict:
        """Analyze trading session performance"""
        logger.info("\n⏰ Analyzing trading sessions...")
        sessions = {}
        
        for tf, df in data_by_timeframe.items():
            if len(df) < 100:
                continue
            
            try:
                df['hour'] = df.index.hour
                df['return'] = df['close'].pct_change()
                
                # Define sessions (UTC)
                session_performance = {
                    'asian': df[(df['hour'] >= 0) & (df['hour'] < 8)]['return'],
                    'london': df[(df['hour'] >= 8) & (df['hour'] < 16)]['return'],
                    'new_york': df[(df['hour'] >= 13) & (df['hour'] < 21)]['return'],
                    'overlap': df[(df['hour'] >= 13) & (df['hour'] < 16)]['return']
                }
                
                session_stats = {}
                for session_name, returns in session_performance.items():
                    valid_returns = returns.dropna()
                    if len(valid_returns) > 10:
                        session_stats[session_name] = {
                            'mean_return': float(valid_returns.mean()),
                            'volatility': float(valid_returns.std()),
                            'win_rate': float((valid_returns > 0).sum() / len(valid_returns)),
                            'total_moves': len(valid_returns)
                        }
                
                sessions[tf] = session_stats
                london_wr = session_stats.get('london', {}).get('win_rate', 0)
                ny_wr = session_stats.get('new_york', {}).get('win_rate', 0)
                logger.info(f"  {tf}: London WR: {london_wr:.2%}, NY WR: {ny_wr:.2%}")
            except Exception as e:
                logger.warning(f"  {tf}: Session analysis error: {e}")
        
        return sessions
    
    def _analyze_rsi_levels(self, data_by_timeframe: Dict, pair: str) -> Dict:
        """Discover optimal RSI oversold/overbought levels"""
        logger.info("\n📉 Analyzing RSI levels...")
        rsi_analysis = {}
        
        for tf, df in data_by_timeframe.items():
            if len(df) < 50:
                continue
            
            try:
                # Calculate RSI
                delta = df['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss.replace(0, np.nan)
                df['rsi'] = 100 - (100 / (1 + rs))
                
                # Find RSI levels where reversals actually happened
                df['price_change'] = df['close'].pct_change().shift(-1)  # Next period return
                
                # Test different RSI thresholds
                best_oversold = 30
                best_overbought = 70
                best_score = 0
                
                for oversold in range(15, 35, 2):
                    for overbought in range(65, 85, 2):
                        oversold_mask = (df['rsi'] < oversold) & (df['rsi'].notna())
                        overbought_mask = (df['rsi'] > overbought) & (df['rsi'].notna())
                        
                        oversold_periods = df[oversold_mask]
                        overbought_periods = df[overbought_mask]
                        
                        if len(oversold_periods) > 5 and len(overbought_periods) > 5:
                            oversold_reversals = (oversold_periods['price_change'] > 0).sum()
                            oversold_success_rate = oversold_reversals / len(oversold_periods)
                            
                            overbought_reversals = (overbought_periods['price_change'] < 0).sum()
                            overbought_success_rate = overbought_reversals / len(overbought_periods)
                            
                            score = (oversold_success_rate + overbought_success_rate) / 2
                            
                            if score > best_score:
                                best_score = score
                                best_oversold = oversold
                                best_overbought = overbought
                
                rsi_analysis[tf] = {
                    'optimal_oversold': int(best_oversold),
                    'optimal_overbought': int(best_overbought),
                    'reversal_success_rate': float(best_score)
                }
                logger.info(f"  {tf}: RSI({best_oversold}/{best_overbought}), Success rate: {best_score:.2%}")
            except Exception as e:
                logger.warning(f"  {tf}: RSI analysis error: {e}")
        
        return rsi_analysis
    
    def _synthesize_strategy(self, patterns: Dict, data_by_timeframe: Dict) -> Dict:
        """Synthesize optimal strategy parameters from discovered patterns"""
        logger.info("\n🔧 Synthesizing strategy parameters...")
        
        # Use M15 as primary timeframe (most balanced)
        primary_tf = 'M15'
        if primary_tf not in patterns['trend_analysis']:
            available = list(patterns['trend_analysis'].keys())
            primary_tf = available[0] if available else 'M15'
        
        trend = patterns['trend_analysis'].get(primary_tf, {})
        volatility = patterns['volatility_analysis'].get(primary_tf, {})
        rsi = patterns['rsi_analysis'].get(primary_tf, {})
        cycles = patterns['cycle_analysis'].get(primary_tf, {})
        
        params = {
            'ema_fast': trend.get('best_ema_fast', 3),
            'ema_slow': trend.get('best_ema_slow', 12),
            'rsi_oversold': rsi.get('optimal_oversold', 20),
            'rsi_overbought': rsi.get('optimal_overbought', 80),
            'atr_multiplier': volatility.get('optimal_atr_multiplier', 1.5),
            'risk_reward_ratio': 3.0,  # Standard, can be optimized
            'best_trading_hours': cycles.get('best_hours', [8, 9, 10, 13, 14, 15]),
            'best_trading_days': cycles.get('best_days', [0, 1, 2, 3, 4])
        }
        
        logger.info(f"  Discovered: EMA({params['ema_fast']}/{params['ema_slow']}), RSI({params['rsi_oversold']}-{params['rsi_overbought']}), ATRx{params['atr_multiplier']:.2f}")
        
        return params
    
    def _backtest_discovered_strategy(self, pair: str, params: Dict, data_by_timeframe: Dict, patterns: Dict = None) -> Dict:
        """Backtest the discovered strategy"""
        try:
            # Get primary timeframe data (M15 preferred, fallback to available)
            primary_tf = 'M15'
            if primary_tf not in data_by_timeframe:
                # Prefer M5 over H1 for more data points
                if 'M5' in data_by_timeframe:
                    primary_tf = 'M5'
                else:
                    primary_tf = list(data_by_timeframe.keys())[0]
            
            # Use provided patterns or get from results
            if patterns is None:
                patterns = self.results.get(pair, {}).get('patterns', {}) if pair in self.results else {}
            
            # Convert DataFrame back to candles format for backtest
            # Need to reconstruct bid/ask from mid prices (use small spread)
            df = data_by_timeframe[primary_tf]
            candles = []
            
            # Estimate spread (typically 0.0001-0.0002 for major pairs, 0.5-1.0 for gold)
            if 'XAU' in pair:
                spread = 0.5
            elif 'JPY' in pair:
                spread = 0.01  # JPY pairs use 2 decimals
            else:
                spread = 0.0001
            
            for idx, row in df.iterrows():
                mid = row['close']
                bid = mid - (spread / 2)
                ask = mid + (spread / 2)
                
                candles.append({
                    'timestamp': idx,
                    'bid_open': row['open'] - (spread / 2),
                    'bid_high': row['high'] - (spread / 2),
                    'bid_low': row['low'] - (spread / 2),
                    'bid_close': bid,
                    'ask_open': row['open'] + (spread / 2),
                    'ask_high': row['high'] + (spread / 2),
                    'ask_low': row['low'] + (spread / 2),
                    'ask_close': ask,
                    'mid_open': row['open'],
                    'mid_high': row['high'],
                    'mid_low': row['low'],
                    'mid_close': mid,
                    'volume': row.get('volume', 0),
                    'complete': True
                })
            
            # Setup strategy with discovered parameters
            strategy = get_strategy_rank_1()
            strategy.instrument = pair
            strategy.instruments = [pair]
            strategy.ema_fast = params['ema_fast']
            strategy.ema_slow = params['ema_slow']
            strategy.rsi_oversold = params['rsi_oversold']
            strategy.rsi_overbought = params['rsi_overbought']
            strategy.atr_multiplier = params['atr_multiplier']
            strategy.risk_reward_ratio = params['risk_reward_ratio']
            strategy._is_trading_session = lambda: True  # Disable session filter for backtest
            strategy.news_enabled = False  # Disable news filter for backtest
            
            # Lower confidence threshold for discovered strategy
            if hasattr(strategy, 'min_confidence'):
                strategy.min_confidence = 0.15
            if hasattr(strategy, 'min_momentum'):
                strategy.min_momentum = 0.0001
            if hasattr(strategy, 'min_adx'):
                strategy.min_adx = 8.0
            
            # Patch _create_trade_signal to create TradeSignal without 'strength' parameter
            original_create_signal = strategy._create_trade_signal
            def patched_create_signal(optimized_signal, market_data):
                # Manually create TradeSignal without strength parameter
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
                    instrument=strategy.instrument,
                    side=side,
                    units=100000,
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    confidence=max(0.15, optimized_signal.confidence),
                    strategy_name=strategy.name,
                )
            strategy._create_trade_signal = patched_create_signal
            
            # Calculate dynamic confidence threshold from discovered patterns
            # Try to get pattern data - check multiple timeframes if needed
            rsi_success_rate = 0.5
            trend_consistency = 0.5
            
            if patterns:
                # Try primary timeframe first
                rsi_data = patterns.get('rsi_analysis', {}).get(primary_tf, {})
                if not rsi_data and 'rsi_analysis' in patterns:
                    # Try first available timeframe
                    available_tf = list(patterns['rsi_analysis'].keys())[0] if patterns['rsi_analysis'] else None
                    if available_tf:
                        rsi_data = patterns['rsi_analysis'][available_tf]
                
                if rsi_data:
                    rsi_success_rate = rsi_data.get('reversal_success_rate', 0.5)
                
                # Get trend consistency
                trend_data = patterns.get('trend_analysis', {}).get(primary_tf, {})
                if not trend_data and 'trend_analysis' in patterns:
                    available_tf = list(patterns['trend_analysis'].keys())[0] if patterns['trend_analysis'] else None
                    if available_tf:
                        trend_data = patterns['trend_analysis'][available_tf]
                
                if trend_data:
                    trend_consistency = trend_data.get('trend_consistency', 0.5)
            
            # Combine pattern quality metrics
            pattern_quality_score = (rsi_success_rate + trend_consistency) / 2
            
            # Dynamic confidence threshold: better patterns = lower threshold needed
            if pattern_quality_score >= 0.75:
                confidence_threshold = 0.10  # Excellent patterns - trust low confidence
            elif pattern_quality_score >= 0.70:
                confidence_threshold = 0.12  # Very good patterns
            elif pattern_quality_score >= 0.65:
                confidence_threshold = 0.15  # Good patterns
            elif pattern_quality_score >= 0.60:
                confidence_threshold = 0.18  # Decent patterns
            elif pattern_quality_score >= 0.55:
                confidence_threshold = 0.20  # Moderate patterns
            else:
                confidence_threshold = 0.22  # Lower quality - slightly higher threshold
            
            logger.info(f"  📊 Pattern Quality: {pattern_quality_score:.1%} (RSI: {rsi_success_rate:.1%}, Trend: {trend_consistency:.1%})")
            logger.info(f"  🎯 Dynamic Confidence Threshold: {confidence_threshold:.2f}")
            
            # Patch _generate_signal to boost confidence for discovered patterns
            original_generate_signal = strategy._generate_signal
            def enhanced_generate_signal(market_data):
                signal = original_generate_signal(market_data)
                if signal:
                    # Boost confidence calculation - discovered patterns are more reliable
                    # Original: confidence = strength * 0.8 + 0.2
                    # Enhanced: better base and scaling
                    original_conf = signal.confidence
                    
                    # Additional boost if RSI is in optimal zone for discovered pattern
                    rsi_optimal_lo = params['rsi_oversold']
                    rsi_optimal_hi = params['rsi_overbought']
                    
                    if signal.signal == 'BUY' and rsi_optimal_lo < signal.rsi < rsi_optimal_hi:
                        # RSI in optimal reversal zone, boost confidence
                        signal.confidence = min(1.0, signal.confidence * 1.4)
                    elif signal.signal == 'SELL' and rsi_optimal_lo < signal.rsi < rsi_optimal_hi:
                        signal.confidence = min(1.0, signal.confidence * 1.4)
                    
                    # Minimum confidence boost from pattern quality
                    signal.confidence = max(signal.confidence, confidence_threshold)
                    
                    logger.debug(f"  Confidence: {original_conf:.2f} → {signal.confidence:.2f} (pattern boost)")
                
                return signal
            strategy._generate_signal = enhanced_generate_signal
            
            # Patch analyze_market to use dynamic confidence threshold
            original_analyze_market = strategy.analyze_market
            def relaxed_analyze_market(market_data):
                try:
                    strategy._reset_daily_counters()
                    
                    # Check daily trade limit
                    if strategy.daily_trade_count >= strategy.max_daily_trades:
                        return []
                    
                    # Check if it's our instrument
                    if strategy.instrument not in market_data:
                        return []
                    
                    current_data = market_data[strategy.instrument]
                    
                    # Update indicators
                    strategy._update_indicators(current_data)
                    
                    # Generate signal (with enhanced confidence calculation)
                    optimized_signal = strategy._generate_signal(current_data)
                    
                    if optimized_signal:
                        # Use dynamic threshold - accept if above pattern-based threshold
                        # (Threshold is already applied in enhanced_generate_signal)
                        try:
                            trade_signal = strategy._create_trade_signal(optimized_signal, current_data)
                            strategy.signals.append(trade_signal)
                            strategy.daily_trade_count += 1
                            return [trade_signal]
                        except Exception as e:
                            logger.warning(f"Error creating trade signal: {e}")
                            return []
                    
                    return []
                except Exception as e:
                    logger.error(f"Analysis error: {e}")
                    return []
            
            strategy.analyze_market = relaxed_analyze_market
            
            # Reset EMA history for new periods
            strategy.ema_history = {strategy.ema_fast: [], strategy.ema_slow: []}
            strategy.price_history = []
            strategy.rsi_history = []
            strategy.atr_history = []
            
            # Run backtest
            result = run_backtest(strategy, {pair: candles}, days=self.days)
            
            return {
                'trades': result.get('trades', 0),
                'win_rate': result.get('win_rate', 0),
                'profit_factor': result.get('profit_factor', 0),
                'total_profit': result.get('total_profit', 0),
                'status': 'ok'
            }
            
        except Exception as e:
            logger.error(f"❌ Backtest error for {pair}: {e}", exc_info=True)
            return {'status': 'error', 'error': str(e), 'trades': 0, 'win_rate': 0, 'profit_factor': 0, 'total_profit': 0}


def main():
    """Main execution"""
    print("\n" + "="*80)
    print("🔍 MARKET PATTERN DISCOVERY ENGINE")
    print("="*80)
    print(f"Analyzing last 30 days to discover patterns and synthesize strategies")
    print(f"Testing each pair individually on their own merit")
    print(f"Results will be sent to Telegram incrementally")
    print("="*80)
    
    if not load_credentials():
        logger.error("❌ Failed to load credentials")
        return
    
    discovery = MarketPatternDiscovery(days=30)
    output_file = discovery.discover_all_pairs()
    
    print(f"\n✅ Analysis complete! Results saved to: {output_file}")


if __name__ == '__main__':
    main()

