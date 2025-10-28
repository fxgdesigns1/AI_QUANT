#!/usr/bin/env python3
"""
Enhanced Monte Carlo Parameter Optimizer with Contextual Awareness
Test 1000+ parameter combinations with session quality and news filtering
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import random
import logging
import yaml
from typing import Dict, List, Tuple, Optional
import numpy as np
from datetime import datetime, timedelta
import pytz
import json

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load credentials
try:
    with open('app.yaml') as f:
        config = yaml.safe_load(f)
        os.environ['OANDA_API_KEY'] = config['env_variables']['OANDA_API_KEY']
    with open('accounts.yaml') as f:
        accounts = yaml.safe_load(f)
        os.environ['OANDA_ACCOUNT_ID'] = accounts['accounts'][0]['id']
    logger.info("✅ Credentials loaded")
except Exception as e:
    logger.error(f"❌ Failed to load credentials: {e}")
    sys.exit(1)

# Import core modules
from src.core.historical_fetcher import get_historical_fetcher
from validate_strategy import StrategyValidator

# Import contextual modules
try:
    from src.core.session_manager import get_session_manager
    from src.core.historical_news_fetcher import get_historical_news_fetcher
    logger.info("✅ Contextual modules imported")
except Exception as e:
    logger.error(f"❌ Failed to import contextual modules: {e}")
    sys.exit(1)


class ContextualMonteCarloOptimizer:
    """
    Enhanced Monte Carlo Optimizer with Session and News Awareness
    
    Features:
    - Session quality filtering
    - News event avoidance
    - Time-of-day optimization
    - Multi-objective fitness function
    """
    
    def __init__(self, strategy_name: str, strategy_module: str, 
                strategy_function: str, instruments: List[str],
                historical_data: Dict, lookback_days: int = 7):
        """Initialize the optimizer"""
        self.strategy_name = strategy_name
        self.strategy_module = strategy_module
        self.strategy_function = strategy_function
        self.instruments = instruments
        self.historical_data = historical_data
        self.lookback_days = lookback_days
        
        # Initialize contextual modules
        self.session_manager = get_session_manager()
        self.news_fetcher = get_historical_news_fetcher()
        
        # Set up validator
        hours = lookback_days * 24
        self.validator = StrategyValidator(strategy_name, lookback_hours=hours)
        
        # Extract timestamps from historical data
        self.timestamps = []
        for instrument in instruments:
            if instrument in historical_data and historical_data[instrument]:
                self.timestamps = [c['time'] for c in historical_data[instrument]]
                break
        
        # Process timestamps to get session quality and news context
        self.process_contextual_data()
        
        logger.info(f"✅ Contextual Monte Carlo Optimizer initialized for {strategy_name}")
    
    def process_contextual_data(self):
        """Process timestamps to get session quality and news context"""
        self.session_qualities = {}
        self.news_events = {}
        
        logger.info("📊 Processing session quality for historical data...")
        for timestamp_str in self.timestamps:
            try:
                # Convert string timestamp to datetime
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                
                # Get session quality
                quality, _ = self.session_manager.get_session_quality(timestamp)
                self.session_qualities[timestamp_str] = quality
                
                # Get news context (high impact events within 1 hour)
                for instrument in self.instruments:
                    news_context = self.news_fetcher.get_instrument_news(
                        instrument, timestamp, lookback_hours=1, lookahead_hours=1
                    )
                    
                    # Check for high impact events
                    has_high_impact = news_context.get('high_impact_count', 0) > 0 or \
                                     news_context.get('high_impact_upcoming', False)
                    
                    if timestamp_str not in self.news_events:
                        self.news_events[timestamp_str] = {}
                    
                    self.news_events[timestamp_str][instrument] = has_high_impact
            except Exception as e:
                logger.warning(f"⚠️ Error processing timestamp {timestamp_str}: {e}")
        
        logger.info(f"✅ Processed {len(self.session_qualities)} timestamps for session quality")
        logger.info(f"✅ Processed news events for {len(self.instruments)} instruments")
    
    def optimize(self, iterations: int = 1000, 
                session_filter: bool = True, 
                news_filter: bool = True,
                target_trades_per_day: float = 5.0) -> List[Dict]:
        """
        Run Monte Carlo optimization with contextual awareness
        
        Args:
            iterations: Number of random parameter combinations to test
            session_filter: Whether to include session quality in optimization
            news_filter: Whether to include news filtering in optimization
            target_trades_per_day: Target number of trades per day
            
        Returns:
            List of top 10 parameter configurations
        """
        logger.info(f"🎲 CONTEXTUAL MONTE CARLO OPTIMIZATION - {self.strategy_name.upper()}")
        logger.info("=" * 80)
        logger.info(f"Iterations: {iterations}")
        logger.info(f"Target: ~{target_trades_per_day} trades per day")
        logger.info(f"Session Filter: {'Enabled' if session_filter else 'Disabled'}")
        logger.info(f"News Filter: {'Enabled' if news_filter else 'Disabled'}")
        logger.info("")
        
        # Parameter ranges to test - FIXED OCT 17: More realistic ranges
        param_ranges = {
            # Core parameters
            'min_adx': (5, 18),                # ADX threshold (was 8-30, TOO HIGH!)
            'min_momentum': (0.0003, 0.008),   # 0.03% to 0.8% (realistic for 3.5h periods)
            'min_volume': (0.05, 0.40),        # 5% to 40% above average
            'quality_threshold': (10, 50),     # Quality score minimum (was 80, TOO HIGH!)
            
            # Session parameters
            'min_session_quality': (0, 80),    # Minimum session quality (0-100)
            'only_trade_london_ny': (0, 1),    # Boolean (0=false, 1=true)
            
            # News parameters
            'avoid_high_impact_news': (0, 1),  # Boolean (0=false, 1=true)
        }
        
        logger.info("Parameter Ranges:")
        logger.info(f"  ADX: {param_ranges['min_adx'][0]}-{param_ranges['min_adx'][1]}")
        logger.info(f"  Momentum: {param_ranges['min_momentum'][0]*100:.2f}%-{param_ranges['min_momentum'][1]*100:.2f}%")
        logger.info(f"  Volume: {param_ranges['min_volume'][0]:.2f}-{param_ranges['min_volume'][1]:.2f}")
        logger.info(f"  Quality: {param_ranges['quality_threshold'][0]}-{param_ranges['quality_threshold'][1]}")
        
        if session_filter:
            logger.info(f"  Session Quality: {param_ranges['min_session_quality'][0]}-{param_ranges['min_session_quality'][1]}")
            logger.info(f"  London/NY Only: {param_ranges['only_trade_london_ny'][0]}-{param_ranges['only_trade_london_ny'][1]}")
        
        if news_filter:
            logger.info(f"  Avoid News: {param_ranges['avoid_high_impact_news'][0]}-{param_ranges['avoid_high_impact_news'][1]}")
        
        logger.info("")
        logger.info(f"Testing {iterations} random configurations...")
        
        results = []
        days_in_data = self.lookback_days
        
        for i in range(iterations):
            if (i + 1) % 100 == 0:
                logger.info(f"  Progress: {i+1}/{iterations}...")
            
            # Generate random configuration
            test_config = {
                'min_adx': random.uniform(*param_ranges['min_adx']),
                'min_momentum': random.uniform(*param_ranges['min_momentum']),
                'min_volume': random.uniform(*param_ranges['min_volume']),
                'quality_threshold': random.uniform(*param_ranges['quality_threshold'])
            }
            
            # Add session parameters if enabled
            if session_filter:
                test_config['min_session_quality'] = random.uniform(*param_ranges['min_session_quality'])
                test_config['only_trade_london_ny'] = random.uniform(*param_ranges['only_trade_london_ny']) > 0.5
            
            # Add news parameters if enabled
            if news_filter:
                test_config['avoid_high_impact_news'] = random.uniform(*param_ranges['avoid_high_impact_news']) > 0.5
            
            try:
                # Load strategy with test configuration
                module = __import__(self.strategy_module, fromlist=[self.strategy_function])
                get_strategy = getattr(module, self.strategy_function)
                strategy = get_strategy()
                
                # Apply test configuration
                if hasattr(strategy, 'min_adx'):
                    strategy.min_adx = test_config['min_adx']
                if hasattr(strategy, 'min_momentum'):
                    strategy.min_momentum = test_config['min_momentum']
                if hasattr(strategy, 'min_volume'):
                    strategy.min_volume = test_config['min_volume']
                if hasattr(strategy, 'min_quality_score'):
                    strategy.min_quality_score = test_config['quality_threshold']
                
                # Apply session parameters if enabled
                if session_filter:
                    if hasattr(strategy, 'min_session_quality'):
                        strategy.min_session_quality = test_config['min_session_quality']
                    if hasattr(strategy, 'only_trade_london_ny'):
                        strategy.only_trade_london_ny = test_config['only_trade_london_ny']
                
                # Apply news parameters if enabled
                if news_filter:
                    if hasattr(strategy, 'avoid_high_impact_news'):
                        strategy.avoid_high_impact_news = test_config['avoid_high_impact_news']
                
                # Reset strategy state
                if hasattr(strategy, 'price_history'):
                    strategy.price_history = {inst: [] for inst in self.instruments}
                if hasattr(strategy, 'daily_trade_count'):
                    strategy.daily_trade_count = 0
                if hasattr(strategy, 'daily_signals'):
                    strategy.daily_signals = []
                
                # Add contextual filters to strategy
                self._add_contextual_filters(strategy, session_filter, news_filter)
                
                # Test this configuration
                backtest_results = self.validator.run_strategy_backtest(strategy, self.historical_data)
                
                signals_generated = backtest_results['signals_generated']
                avg_quality = backtest_results['avg_quality']
                
                # Calculate signals per day
                signals_per_day = signals_generated / days_in_data if days_in_data > 0 else 0
                
                # Calculate fitness score
                # Enhanced multi-objective fitness function
                fitness = self._calculate_fitness(signals_per_day, avg_quality, target_trades_per_day)
                
                results.append({
                    'config': test_config,
                    'signals': signals_generated,
                    'signals_per_day': signals_per_day,
                    'avg_quality': avg_quality,
                    'fitness': fitness
                })
                
            except Exception as e:
                # Skip failed configurations
                logger.debug(f"Config {i} failed: {e}")
                continue
        
        # Sort by fitness (best first)
        results.sort(key=lambda x: x['fitness'], reverse=True)
        
        # Return top 10
        top_10 = results[:10]
        
        self._print_top_results(top_10, session_filter, news_filter)
        
        return top_10
    
    def _add_contextual_filters(self, strategy, session_filter: bool, news_filter: bool):
        """Add contextual filters to strategy for backtest"""
        if not hasattr(strategy, 'original_generate_signal'):
            # Save original method
            strategy.original_generate_signal = strategy.generate_signal
            
            # Create wrapped method with contextual filters
            def wrapped_generate_signal(market_data):
                # Get timestamp
                timestamp_str = market_data.timestamp
                instrument = market_data.pair
                
                # Apply session filter
                if session_filter and timestamp_str in self.session_qualities:
                    session_quality = self.session_qualities[timestamp_str]
                    min_quality = getattr(strategy, 'min_session_quality', 0)
                    
                    if session_quality < min_quality:
                        return None  # Skip due to low session quality
                
                # Apply news filter
                if news_filter and timestamp_str in self.news_events and instrument in self.news_events[timestamp_str]:
                    has_high_impact = self.news_events[timestamp_str][instrument]
                    avoid_news = getattr(strategy, 'avoid_high_impact_news', False)
                    
                    if avoid_news and has_high_impact:
                        return None  # Skip due to high impact news
                
                # Call original method
                return strategy.original_generate_signal(market_data)
            
            # Replace method
            strategy.generate_signal = wrapped_generate_signal
    
    def _calculate_fitness(self, signals_per_day: float, avg_quality: float, 
                          target_trades_per_day: float) -> float:
        """
        Calculate multi-objective fitness score
        
        Args:
            signals_per_day: Average signals per day
            avg_quality: Average quality score
            target_trades_per_day: Target number of trades per day
            
        Returns:
            Fitness score (higher is better)
        """
        # Target fitness (how close to target trades per day)
        distance_from_target = abs(signals_per_day - target_trades_per_day)
        target_fitness = 1 / (1 + distance_from_target)  # Closer to target = higher score
        
        # Quality fitness (higher quality = higher score)
        quality_fitness = avg_quality / 100 if avg_quality > 0 else 0
        
        # Consistency fitness (bonus for consistent daily signals)
        # This would require tracking daily signal counts
        consistency_fitness = 0.0
        
        # Combined fitness (50% target, 40% quality, 10% consistency)
        fitness = (target_fitness * 0.5) + (quality_fitness * 0.4) + (consistency_fitness * 0.1)
        
        return fitness
    
    def _print_top_results(self, top_results: List[Dict], session_filter: bool, news_filter: bool):
        """Print top results in a formatted table"""
        logger.info("")
        logger.info("=" * 100)
        logger.info("TOP 10 CONFIGURATIONS")
        logger.info("=" * 100)
        logger.info("")
        
        # Build header based on enabled filters
        header = f"{'Rank':<6} {'ADX':<8} {'Momentum':<12} {'Volume':<10} {'Quality':<10}"
        
        if session_filter:
            header += f" {'SessQual':<10} {'LDN/NY':<8}"
        
        if news_filter:
            header += f" {'AvoidNews':<10}"
        
        header += f" {'Trades/Day':<12} {'Fitness'}"
        
        logger.info(header)
        logger.info("-" * 100)
        
        for rank, result in enumerate(top_results, 1):
            cfg = result['config']
            
            # Build row based on enabled filters
            row = f"{rank:<6} {cfg['min_adx']:<8.1f} {cfg['min_momentum']*100:<12.3f}% {cfg['min_volume']:<10.2f} " \
                  f"{cfg['quality_threshold']:<10.1f}"
            
            if session_filter:
                row += f" {cfg['min_session_quality']:<10.1f} {str(cfg['only_trade_london_ny']):<8}"
            
            if news_filter:
                row += f" {str(cfg['avoid_high_impact_news']):<10}"
            
            row += f" {result['signals_per_day']:<12.1f} {result['fitness']:.3f}"
            
            logger.info(row)
        
        logger.info("=" * 100)
        logger.info("")
    
    def save_results(self, results: List[Dict], filename: Optional[str] = None):
        """Save optimization results to file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            filename = f"optimization_{self.strategy_name}_{timestamp}.json"
        
        try:
            with open(filename, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            logger.info(f"✅ Optimization results saved to {filename}")
            return filename
        except Exception as e:
            logger.error(f"❌ Error saving results: {e}")
            return None


def monte_carlo_parameter_search(strategy_name: str, strategy_module: str, 
                                strategy_function: str, instruments: List[str],
                                historical_data: Dict, iterations: int = 1000,
                                session_filter: bool = False,
                                news_filter: bool = False) -> List[Dict]:
    """
    Legacy function for backward compatibility
    
    Use ContextualMonteCarloOptimizer for new code
    """
    optimizer = ContextualMonteCarloOptimizer(
        strategy_name=strategy_name,
        strategy_module=strategy_module,
        strategy_function=strategy_function,
        instruments=instruments,
        historical_data=historical_data,
        lookback_days=len(list(historical_data.values())[0]) / 96 if historical_data else 1
    )
    
    return optimizer.optimize(
        iterations=iterations,
        session_filter=session_filter,
        news_filter=news_filter
    )


if __name__ == "__main__":
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Contextual Monte Carlo Optimizer")
    parser.add_argument("--strategy", default="momentum_trading", help="Strategy name")
    parser.add_argument("--module", default="src.strategies.momentum_trading", help="Strategy module")
    parser.add_argument("--function", default="get_momentum_trading_strategy", help="Strategy function")
    parser.add_argument("--days", type=int, default=7, help="Days to look back")
    parser.add_argument("--iterations", type=int, default=1000, help="Number of iterations")
    parser.add_argument("--session", action="store_true", help="Enable session filtering")
    parser.add_argument("--news", action="store_true", help="Enable news filtering")
    parser.add_argument("--target", type=float, default=5.0, help="Target trades per day")
    args = parser.parse_args()
    
    # Get historical data
    fetcher = get_historical_fetcher()
    instruments = ['XAU_USD', 'EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'NZD_USD']
    
    logger.info(f"📥 Fetching {args.days} days of historical data...")
    historical_data = fetcher.get_recent_data_for_strategy(instruments, hours=args.days * 24)
    
    # Create optimizer
    optimizer = ContextualMonteCarloOptimizer(
        strategy_name=args.strategy,
        strategy_module=args.module,
        strategy_function=args.function,
        instruments=instruments,
        historical_data=historical_data,
        lookback_days=args.days
    )
    
    # Run optimization
    top_configs = optimizer.optimize(
        iterations=args.iterations,
        session_filter=args.session,
        news_filter=args.news,
        target_trades_per_day=args.target
    )
    
    # Save results
    optimizer.save_results(top_configs)
    
    logger.info(f"\n✅ Top configuration found:")
    logger.info(f"   Expected: {top_configs[0]['signals_per_day']:.1f} trades/day")
    logger.info(f"   Quality: {top_configs[0]['avg_quality']:.1f}")
    logger.info(f"   Parameters: {top_configs[0]['config']}")