#!/usr/bin/env python3
"""
Strategy Validator - Test Against Last 4 Hours of Real Market Data
NO MORE 12-HOUR WAITS! Know immediately if strategy will produce signals.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import numpy as np

from src.core.historical_fetcher import get_historical_fetcher
from src.core.data_feed import MarketData

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StrategyValidator:
    """
    Validate strategy against recent historical data
    """
    
    def __init__(self, strategy_name: str, lookback_hours: int = 4):
        """
        Initialize validator
        
        Args:
            strategy_name: Name of strategy to validate
            lookback_hours: How many hours of history to test (default 4)
        """
        self.strategy_name = strategy_name
        self.lookback_hours = lookback_hours
        self.fetcher = get_historical_fetcher()
        
        logger.info(f"✅ Validator initialized for {strategy_name} ({lookback_hours}h lookback)")
    
    def get_historical_data(self, instruments: List[str], hours: int = 4) -> Dict:
        """
        Get last N hours of actual OANDA price data
        
        Returns:
            Dict[instrument → List[candles]]
        """
        return self.fetcher.get_recent_data_for_strategy(instruments, hours)
    
    def run_strategy_backtest(self, strategy, historical_data: Dict) -> Dict:
        """
        Run strategy through historical data and count signals
        
        Args:
            strategy: Strategy instance
            historical_data: Dict[instrument → List[candles]]
        
        Returns:
            Results dict with signals, quality scores, regimes, etc.
        """
        signals_generated = []
        quality_scores = []
        regimes_detected = []
        trades_per_hour = [0, 0, 0, 0]  # 4 hours
        
        # CRITICAL FIX: Disable time-based filters during backtest
        # These filters block ALL signals in validation/Monte Carlo!
        original_time_gap = None
        original_last_trade_time = None
        
        if hasattr(strategy, 'min_time_between_trades_minutes'):
            original_time_gap = strategy.min_time_between_trades_minutes
            strategy.min_time_between_trades_minutes = 0  # Disable during backtest
            logger.info(f"🔧 Disabled 60-min gap filter for backtest (was {original_time_gap})")
        
        if hasattr(strategy, 'last_trade_time'):
            original_last_trade_time = strategy.last_trade_time
            strategy.last_trade_time = None  # Reset
        
        # Feed historical data through strategy
        logger.info(f"🔄 Running {self.strategy_name} through {self.lookback_hours}h historical data...")
        
        # Get the first instrument's data to determine timeline
        first_instrument = list(historical_data.keys())[0]
        num_candles = len(historical_data[first_instrument])
        
        logger.info(f"📊 Processing {num_candles} candles...")
        
        # FIRST: Build up price history for all instruments (need 30+ bars for indicators)
        logger.info("📊 Building price history for indicators...")
        for instrument, candles in historical_data.items():
            if hasattr(strategy, 'price_history'):
                if instrument not in strategy.price_history:
                    strategy.price_history[instrument] = []
                
                # Feed first 30 candles to build history
                for candle in candles[:30]:
                    strategy.price_history[instrument].append(candle['close'])
        
        logger.info(f"✅ Price history built: {len(strategy.price_history.get(list(historical_data.keys())[0], []))} bars per instrument")
        
        # NOW: Process each candle timestamp for signal generation
        for i in range(30, num_candles):  # Start at 30 to have enough history
            # Build market_data dict for this timestamp
            market_data = {}
            
            for instrument, candles in historical_data.items():
                if i < len(candles):
                    candle = candles[i]
                    
                    # Convert to MarketData format
                    market_data[instrument] = MarketData(
                        pair=instrument,
                        bid=candle['bid'],
                        ask=candle['ask'],
                        timestamp=candle.get('time', str(datetime.now())),
                        is_live=False,  # Historical data
                        data_source='OANDA_HISTORICAL',
                        spread=candle['ask'] - candle['bid'],
                        last_update_age=0
                    )
                    
                    # Continue feeding price history
                    if hasattr(strategy, 'price_history'):
                        strategy.price_history[instrument].append(candle['close'])
            
            # Call strategy's analyze_market method
            try:
                signals = strategy.analyze_market(market_data)
                
                if signals:
                    signals_generated.extend(signals)
                    
                    # Extract quality scores if available
                    for signal in signals:
                        if hasattr(signal, 'confidence'):
                            quality_scores.append(signal.confidence * 100)
                    
                    # Track which hour
                    hour_index = min(i // (num_candles // 4), 3)
                    trades_per_hour[hour_index] += len(signals)
                    
                    logger.info(f"  ✅ Candle {i}/{num_candles}: {len(signals)} signals")
                
            except Exception as e:
                logger.debug(f"  ⏭️ Candle {i}: {e}")
                continue
        
        logger.info(f"✅ Backtest complete: {len(signals_generated)} signals generated")
        
        # Restore original time-based filters
        if original_time_gap is not None:
            strategy.min_time_between_trades_minutes = original_time_gap
            logger.info(f"🔧 Restored 60-min gap filter to {original_time_gap}")
        
        if original_last_trade_time is not None:
            strategy.last_trade_time = original_last_trade_time
        
        return {
            'signals_generated': len(signals_generated),
            'quality_scores': quality_scores,
            'avg_quality': np.mean(quality_scores) if quality_scores else 0,
            'regimes_detected': regimes_detected,
            'trades_per_hour': trades_per_hour,
            'would_have_traded': len(signals_generated) > 0
        }
    
    def validate_parameters(self, results: Dict) -> Dict:
        """
        Check if strategy would have produced ~5 trades/day
        
        Returns:
            Validation result with recommendations
        """
        signals_4h = results['signals_generated']
        signals_per_day_est = signals_4h * 6  # 4 hours × 6 = 24 hours
        
        # Target: ~5 trades/day (acceptable 3-10)
        target_min = 3
        target_max = 10
        target_ideal = 5
        
        if target_min <= signals_per_day_est <= target_max:
            valid = True
            adjustment = "OK - No adjustment needed"
        elif signals_per_day_est < target_min:
            valid = False
            shortfall_pct = ((target_ideal - signals_per_day_est) / target_ideal) * 100
            adjustment = f"LOWER thresholds by {shortfall_pct:.0f}% (too strict)"
        else:
            valid = False
            excess_pct = ((signals_per_day_est - target_ideal) / target_ideal) * 100
            adjustment = f"RAISE thresholds by {excess_pct:.0f}% (overtrading)"
        
        return {
            'valid': valid,
            'actual_trades_4h': signals_4h,
            'estimated_per_day': signals_per_day_est,
            'target_range': f'{target_min}-{target_max} trades/day',
            'adjustment_needed': adjustment
        }
    
    def suggest_tuning(self, results: Dict, current_params: Dict) -> Dict:
        """
        Suggest parameter adjustments based on results
        
        Args:
            results: Backtest results
            current_params: Current strategy parameters
        
        Returns:
            Recommended parameter changes
        """
        signals_per_day_est = results['signals_generated'] * 6
        target = 5
        
        # Calculate adjustment percentage needed
        if signals_per_day_est == 0:
            adjust_pct = -40  # Lower by 40%
        elif signals_per_day_est < 3:
            adjust_pct = -25  # Lower by 25%
        elif signals_per_day_est > 10:
            adjust_pct = +20  # Raise by 20%
        elif signals_per_day_est > 15:
            adjust_pct = +30  # Raise by 30%
        else:
            adjust_pct = 0    # OK
        
        # Apply adjustment to parameters
        recommended = {}
        
        for param, value in current_params.items():
            if isinstance(value, (int, float)):
                new_value = value * (1 + adjust_pct / 100)
                recommended[param] = new_value
            else:
                recommended[param] = value
        
        return {
            'adjustment_pct': adjust_pct,
            'current': current_params,
            'recommended': recommended,
            'reason': f'Produces {signals_per_day_est:.1f} trades/day, target is {target}'
        }


def validate_momentum_strategy():
    """
    Validate momentum strategy against last 4 hours
    """
    print("🔍 VALIDATING MOMENTUM STRATEGY")
    print("=" * 80)
    print()
    
    # Step 1: Load current strategy
    from src.strategies.momentum_trading import get_momentum_trading_strategy
    strategy = get_momentum_trading_strategy()
    
    print(f"✅ Loaded strategy: {strategy.name}")
    print(f"📊 Current parameters:")
    print(f"   Min ADX: {strategy.min_adx}")
    print(f"   Min Momentum: {strategy.min_momentum}")
    print(f"   Min Volume: {strategy.min_volume}")
    print(f"   Quality Threshold: {strategy.min_quality_score}")
    print()
    
    # Step 2: Get last 4 hours of market data from OANDA
    validator = StrategyValidator('momentum_trading', lookback_hours=4)
    
    instruments = strategy.instruments
    print(f"📥 Fetching {validator.lookback_hours}-hour history for {len(instruments)} instruments...")
    
    historical_data = validator.get_historical_data(instruments, hours=4)
    
    if not historical_data:
        print("❌ Failed to fetch historical data")
        return {'valid': False}
    
    print(f"✅ Got historical data for {len(historical_data)} instruments")
    print()
    
    # Step 3: Run strategy through data
    print(f"🔄 Running strategy through historical data...")
    results = validator.run_strategy_backtest(strategy, historical_data)
    
    # Step 4: Show results
    print()
    print("📊 BACKTEST RESULTS (Last 4 Hours):")
    print("-" * 80)
    print(f"Signals Generated: {results['signals_generated']}")
    print(f"Quality Scores: {results['quality_scores'][:10] if results['quality_scores'] else 'None'}")
    print(f"Average Quality: {results['avg_quality']:.1f}" if results['avg_quality'] > 0 else "Average Quality: N/A")
    print(f"Trades Per Hour: {results['trades_per_hour']}")
    print(f"Estimated Per Day: {results['signals_generated'] * 6}")
    print()
    
    # Step 5: Validate
    validation = validator.validate_parameters(results)
    
    print("✅ VALIDATION RESULT:")
    print("-" * 80)
    print(f"Valid: {'✅ YES' if validation['valid'] else '❌ NO'}")
    print(f"Actual (4h): {validation['actual_trades_4h']} trades")
    print(f"Estimated/Day: {validation['estimated_per_day']:.1f} trades")
    print(f"Target Range: {validation['target_range']}")
    print(f"Adjustment: {validation['adjustment_needed']}")
    print()
    
    # Step 6: Suggest tuning if needed
    if not validation['valid']:
        current_params = {
            'min_adx': strategy.min_adx,
            'min_momentum': strategy.min_momentum,
            'min_volume': strategy.min_volume,
            'min_quality_score': strategy.min_quality_score
        }
        
        tuning = validator.suggest_tuning(results, current_params)
        
        print("💡 RECOMMENDED TUNING:")
        print("-" * 80)
        print(f"Adjustment: {tuning['adjustment_pct']:+.0f}%")
        print(f"Reason: {tuning['reason']}")
        print()
        print("Current vs Recommended:")
        for param, current_val in tuning['current'].items():
            recommended_val = tuning['recommended'][param]
            change_pct = ((recommended_val - current_val) / current_val * 100) if current_val else 0
            print(f"  {param}: {current_val:.4f} → {recommended_val:.4f} ({change_pct:+.1f}%)")
        print()
    
    return validation


if __name__ == "__main__":
    result = validate_momentum_strategy()
    
    print("=" * 80)
    if result['valid']:
        print("✅ VALIDATION PASSED - Strategy ready to deploy!")
        print("Run: gcloud app deploy ...")
    else:
        print("❌ VALIDATION FAILED - Do NOT deploy yet!")
        print("Fix parameters and run validation again.")
    print("=" * 80)

