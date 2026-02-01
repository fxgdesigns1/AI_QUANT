#!/usr/bin/env python3
"""
Universal Monte Carlo Strategy Optimizer
Optimizes any trading strategy by testing parameter combinations against historical data
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
import itertools
import json
import yaml

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.oanda_client import OandaClient
from src.core.data_feed import MarketData


def load_credentials_from_yaml():
    """Load OANDA credentials from app.yaml if not in environment"""
    if os.getenv('OANDA_API_KEY') and os.getenv('OANDA_ACCOUNT_ID'):
        return  # Already set
    
    try:
        with open('app.yaml', 'r') as f:
            app_config = yaml.safe_load(f)
            env_vars = app_config.get('env_variables', {})
            
            if not os.getenv('OANDA_API_KEY'):
                os.environ['OANDA_API_KEY'] = env_vars.get('OANDA_API_KEY', '')
            if not os.getenv('OANDA_ACCOUNT_ID'):
                # Try to load from accounts.yaml
                with open('accounts.yaml', 'r') as af:
                    accounts_config = yaml.safe_load(af)
                    accounts = accounts_config.get('accounts', [])
                    if accounts:
                        os.environ['OANDA_ACCOUNT_ID'] = accounts[0]['id']
            if not os.getenv('OANDA_ENVIRONMENT'):
                os.environ['OANDA_ENVIRONMENT'] = env_vars.get('OANDA_ENVIRONMENT', 'practice')
                
            logger.info("✅ Loaded credentials from app.yaml")
    except Exception as e:
        logger.error(f"❌ Failed to load credentials: {str(e)}")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class UniversalOptimizer:
    """Monte Carlo optimizer that works with any strategy class"""
    
    def __init__(self, strategy_class, strategy_name: str, instruments: List[str]):
        # Load credentials from app.yaml if needed
        load_credentials_from_yaml()
        
        self.strategy_class = strategy_class
        self.strategy_name = strategy_name
        self.instruments = instruments
        self.oanda_client = OandaClient(
            api_key=os.getenv('OANDA_API_KEY'),
            account_id=os.getenv('OANDA_ACCOUNT_ID'),
            environment=os.getenv('OANDA_ENVIRONMENT', 'practice')
        )
        
    def download_historical_data(self, days: int = 7) -> Dict[str, List[Dict]]:
        """Download historical candles for all instruments"""
        logger.info(f"📥 Downloading {days} days of historical data for {len(self.instruments)} instruments...")
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)
        
        historical_data = {}
        
        for instrument in self.instruments:
            logger.info(f"  Fetching {instrument}...")
            try:
                result = self.oanda_client.get_candles(
                    instrument=instrument,
                    granularity='M5',
                    count=days * 288  # 288 M5 candles per day
                )
                candles = result.get('candles', []) if result else []
                
                if candles:
                    historical_data[instrument] = candles
                    logger.info(f"  ✅ {instrument}: {len(candles)} candles")
                else:
                    logger.warning(f"  ⚠️ {instrument}: No data received")
                    
            except Exception as e:
                logger.error(f"  ❌ {instrument}: {str(e)}")
                
        return historical_data
    
    def create_param_combinations(self, param_ranges: Dict[str, List]) -> List[Dict]:
        """Generate all combinations of parameters for Monte Carlo simulation"""
        keys = list(param_ranges.keys())
        values = [param_ranges[k] for k in keys]
        
        combinations = []
        for combo in itertools.product(*values):
            param_dict = dict(zip(keys, combo))
            combinations.append(param_dict)
            
        logger.info(f"🎲 Generated {len(combinations)} parameter combinations")
        return combinations
    
    def backtest_with_params(
        self,
        params: Dict[str, Any],
        historical_data: Dict[str, List[Dict]]
    ) -> Dict[str, Any]:
        """Run backtest with specific parameter set"""
        
        # Create strategy instance with custom parameters
        strategy = self.strategy_class()
        
        # Apply parameters to strategy
        for param_name, param_value in params.items():
            if hasattr(strategy, param_name):
                setattr(strategy, param_name, param_value)
        
        # Temporarily disable time-based filters for backtesting
        original_time_filter = getattr(strategy, 'min_time_between_trades_minutes', None)
        if hasattr(strategy, 'min_time_between_trades_minutes'):
            strategy.min_time_between_trades_minutes = 0
        
        # Initialize price history
        strategy.price_history = {inst: [] for inst in self.instruments}
        
        # Collect all timestamps across instruments
        all_timestamps = set()
        for instrument, candles in historical_data.items():
            for candle in candles:
                all_timestamps.add(candle['time'])
        
        sorted_timestamps = sorted(all_timestamps)
        
        # Results tracking
        trades = []
        open_positions = {}
        total_signals_seen = 0
        
        # Process each timestamp
        for timestamp in sorted_timestamps:
            # Build market data for this timestamp
            market_data_dict = {}
            
            for instrument in self.instruments:
                if instrument not in historical_data:
                    continue
                    
                # Find candle for this timestamp
                candle = None
                for c in historical_data[instrument]:
                    if c['time'] == timestamp:
                        candle = c
                        break
                
                if candle:
                    # Extract close price from OANDA format
                    close_price = float(candle.get('mid', {}).get('c') or candle.get('bid', {}).get('c', 0))
                    if close_price == 0:  # Fallback if mid/bid not available
                        close_price = (float(candle.get('bid', {}).get('c', 0)) + float(candle.get('ask', {}).get('c', 0))) / 2
                    
                    # Update price history
                    strategy.price_history[instrument].append(close_price)
                    
                    # Keep only recent history
                    if len(strategy.price_history[instrument]) > 200:
                        strategy.price_history[instrument] = strategy.price_history[instrument][-200:]
                    
                    # Create market data
                    bid_price = float(candle.get('bid', {}).get('c', close_price))
                    ask_price = float(candle.get('ask', {}).get('c', close_price))
                    
                    market_data_dict[instrument] = MarketData(
                        pair=instrument,
                        bid=bid_price,
                        ask=ask_price,
                        spread=ask_price - bid_price,
                        timestamp=timestamp,
                        is_live=False,
                        data_source='OANDA_Historical',
                        last_update_age=0
                    )
            
            # Generate signals
            if market_data_dict:
                try:
                    signals = strategy.analyze_market(market_data_dict)
                    
                    if signals:
                        total_signals_seen += len(signals)
                        logger.info(f"📊 Got {len(signals)} signals at timestamp {timestamp}")
                    
                    # Process new signals
                    for signal in signals:
                        instrument = signal.instrument
                        if instrument not in open_positions:
                            # Get current price from market data
                            current_price = market_data_dict[instrument].bid
                            
                            # Open new position
                            open_positions[instrument] = {
                                'entry_price': current_price,
                                'direction': signal.side.value,  # OrderSide enum
                                'stop_loss': signal.stop_loss,
                                'take_profit': signal.take_profit,
                                'entry_time': timestamp,
                                'pair': instrument
                            }
                            logger.info(f"🔵 OPENED {signal.side.value} on {instrument} @ {current_price}")
                            
                except Exception as e:
                    logger.debug(f"Signal generation error: {str(e)}")
                    pass
            
            # Check open positions for exits
            closed_positions = []
            for pair, position in list(open_positions.items()):
                if pair in market_data_dict:
                    current_price = market_data_dict[pair].bid
                    
                    # Check if stop loss or take profit hit
                    if position['direction'] == 'BUY':
                        if current_price <= position['stop_loss']:
                            # Stop loss hit
                            pnl = position['stop_loss'] - position['entry_price']
                            trades.append({
                                'pair': pair,
                                'entry_price': position['entry_price'],
                                'exit_price': position['stop_loss'],
                                'pnl': pnl,
                                'result': 'loss',
                                'entry_time': position['entry_time'],
                                'exit_time': timestamp
                            })
                            logger.info(f"❌ CLOSED LOSS on {pair} @ {current_price} (SL hit)")
                            closed_positions.append(pair)
                        elif current_price >= position['take_profit']:
                            # Take profit hit
                            pnl = position['take_profit'] - position['entry_price']
                            trades.append({
                                'pair': pair,
                                'entry_price': position['entry_price'],
                                'exit_price': position['take_profit'],
                                'pnl': pnl,
                                'result': 'win',
                                'entry_time': position['entry_time'],
                                'exit_time': timestamp
                            })
                            logger.info(f"✅ CLOSED WIN on {pair} @ {current_price} (TP hit)")
                            closed_positions.append(pair)
                    else:  # SELL
                        if current_price >= position['stop_loss']:
                            # Stop loss hit
                            pnl = position['entry_price'] - position['stop_loss']
                            trades.append({
                                'pair': pair,
                                'entry_price': position['entry_price'],
                                'exit_price': position['stop_loss'],
                                'pnl': pnl,
                                'result': 'loss',
                                'entry_time': position['entry_time'],
                                'exit_time': timestamp
                            })
                            closed_positions.append(pair)
                        elif current_price <= position['take_profit']:
                            # Take profit hit
                            pnl = position['entry_price'] - position['take_profit']
                            trades.append({
                                'pair': pair,
                                'entry_price': position['entry_price'],
                                'exit_price': position['take_profit'],
                                'pnl': pnl,
                                'result': 'win',
                                'entry_time': position['entry_time'],
                                'exit_time': timestamp
                            })
                            closed_positions.append(pair)
            
            # Remove closed positions
            for pair in closed_positions:
                del open_positions[pair]
        
        # Restore original settings
        if original_time_filter is not None:
            strategy.min_time_between_trades_minutes = original_time_filter
        
        logger.info(f"📈 Backtest complete: {total_signals_seen} signals seen, {len(trades)} trades closed")
        
        # Calculate metrics
        total_trades = len(trades)
        if total_trades == 0:
            return {
                'params': params,
                'total_trades': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'score': 0
            }
        
        wins = [t for t in trades if t['result'] == 'win']
        losses = [t for t in trades if t['result'] == 'loss']
        
        win_count = len(wins)
        loss_count = len(losses)
        win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0
        
        total_pnl = sum(t['pnl'] for t in trades)
        avg_win = sum(t['pnl'] for t in wins) / len(wins) if wins else 0
        avg_loss = sum(t['pnl'] for t in losses) / len(losses) if losses else 0
        
        # Calculate score (combines win rate, profit, and trade frequency)
        score = (win_rate * 0.4) + (total_pnl * 10000 * 0.4) + (total_trades * 0.2)
        
        return {
            'params': params,
            'total_trades': total_trades,
            'win_count': win_count,
            'loss_count': loss_count,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'score': score,
            'trades': trades
        }
    
    def optimize(
        self,
        param_ranges: Dict[str, List],
        days: int = 7,
        top_n: int = 5
    ) -> List[Dict]:
        """Run Monte Carlo optimization"""
        
        logger.info(f"\n{'='*70}")
        logger.info(f"🎯 OPTIMIZING STRATEGY: {self.strategy_name}")
        logger.info(f"{'='*70}\n")
        
        # Step 1: Download historical data
        historical_data = self.download_historical_data(days)
        
        if not historical_data:
            logger.error("❌ No historical data available!")
            return []
        
        # Step 2: Generate parameter combinations
        param_combinations = self.create_param_combinations(param_ranges)
        
        # Step 3: Run Monte Carlo simulation
        logger.info(f"\n🔬 Running {len(param_combinations)} simulations...")
        results = []
        
        for i, params in enumerate(param_combinations, 1):
            if i % 10 == 0:
                logger.info(f"  Progress: {i}/{len(param_combinations)} ({i/len(param_combinations)*100:.1f}%)")
            
            try:
                result = self.backtest_with_params(params, historical_data)
                results.append(result)
            except Exception as e:
                logger.debug(f"  Simulation {i} failed: {str(e)}")
                continue
        
        # Step 4: Rank results
        results.sort(key=lambda x: x['score'], reverse=True)
        
        # Step 5: Display top results
        logger.info(f"\n{'='*70}")
        logger.info(f"🏆 TOP {top_n} PARAMETER SETS")
        logger.info(f"{'='*70}\n")
        
        for i, result in enumerate(results[:top_n], 1):
            logger.info(f"\n--- Rank #{i} (Score: {result['score']:.2f}) ---")
            logger.info(f"Parameters: {json.dumps(result['params'], indent=2)}")
            logger.info(f"Total Trades: {result['total_trades']}")
            logger.info(f"Win Rate: {result['win_rate']:.1f}%")
            logger.info(f"Total P&L: {result['total_pnl']:.5f}")
            logger.info(f"Avg Win: {result['avg_win']:.5f}")
            logger.info(f"Avg Loss: {result['avg_loss']:.5f}")
        
        return results[:top_n]


def main():
    """Example usage"""
    from src.strategies.momentum_trading import MomentumTradingStrategy
    
    optimizer = UniversalOptimizer(
        strategy_class=MomentumTradingStrategy,
        strategy_name="Momentum Trading",
        instruments=['EUR_USD', 'GBP_USD', 'USD_JPY', 'XAU_USD']
    )
    
    param_ranges = {
        'stop_loss_atr': [1.5, 2.0, 2.5, 3.0],
        'take_profit_atr': [5.0, 10.0, 15.0, 20.0],
        'min_adx': [5.0, 8.0, 10.0, 15.0],
        'min_momentum': [0.0001, 0.0003, 0.0005, 0.001],
        'momentum_period': [30, 40, 50, 60],
        'trend_period': [60, 80, 100, 120],
        'min_quality_score': [5, 10, 15, 20]
    }
    
    top_results = optimizer.optimize(param_ranges, days=7, top_n=5)


if __name__ == '__main__':
    main()

