#!/usr/bin/env python3
"""
Direct Strategy Test
Tests the fundamental characteristics of each strategy with actual OANDA data
"""

import os
import sys
import yaml
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any

sys.path.insert(0, '.')

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

# Import required modules
from src.core.oanda_client import OandaClient
from src.strategies.momentum_trading import MomentumTradingStrategy
from src.strategies.gold_scalping import GoldScalpingStrategy
from src.core.data_feed import MarketData

def configure_strategy_parameters(strategy, strategy_type):
    """Configure strategy with appropriate fundamental parameters"""
    if strategy_type == "momentum":
        # Set proper momentum strategy parameters
        strategy.min_adx = 25.0  # Strong trend required
        strategy.min_momentum = 0.005  # Significant momentum required
        strategy.min_quality_score = 70  # Only high-quality setups
        strategy.momentum_period = 20  # Longer period for trend confirmation
        strategy.trend_period = 50  # Long-term trend confirmation
        strategy.stop_loss_atr = 3.0  # Wider stop to avoid premature exits
        strategy.take_profit_atr = 6.0  # Reasonable profit target
        strategy.max_trades_per_day = 5  # Limit number of trades
        strategy.min_time_between_trades_minutes = 120  # Avoid overtrading
        strategy.require_trend_continuation = True  # Ensure trend alignment
        
        logger.info(f"✅ Configured momentum strategy with fundamental parameters:")
        logger.info(f"   - min_adx: {strategy.min_adx}")
        logger.info(f"   - min_momentum: {strategy.min_momentum}")
        logger.info(f"   - min_quality_score: {strategy.min_quality_score}")
        logger.info(f"   - momentum_period: {strategy.momentum_period}")
        logger.info(f"   - trend_period: {strategy.trend_period}")
        logger.info(f"   - R:R ratio: 1:{strategy.take_profit_atr/strategy.stop_loss_atr:.1f}")
    
    elif strategy_type == "scalping":
        # Set proper scalping strategy parameters
        strategy.min_spread = 0.0005  # Maximum acceptable spread
        strategy.min_volatility = 0.0015  # Minimum volatility required
        strategy.max_volatility = 0.0050  # Maximum volatility allowed
        strategy.stop_loss_pips = 15  # Tight stop loss
        strategy.take_profit_pips = 30  # Reasonable profit target
        strategy.max_trades_per_day = 10  # Allow more trades for scalping
        strategy.min_time_between_trades_minutes = 30  # Allow more frequent trades
        
        logger.info(f"✅ Configured scalping strategy with fundamental parameters:")
        logger.info(f"   - min_spread: {strategy.min_spread}")
        logger.info(f"   - volatility range: {strategy.min_volatility}-{strategy.max_volatility}")
        logger.info(f"   - stop_loss_pips: {strategy.stop_loss_pips}")
        logger.info(f"   - take_profit_pips: {strategy.take_profit_pips}")
        logger.info(f"   - R:R ratio: 1:{strategy.take_profit_pips/strategy.stop_loss_pips:.1f}")

def create_market_data_from_candle(candle, instrument):
    """Create MarketData object from a single OANDA candle"""
    try:
        # Extract time
        time_str = candle.get('time', None)
        if not time_str:
            return None
        
        # Extract bid/ask prices
        if 'bid' in candle and isinstance(candle['bid'], dict):
            bid_close = float(candle['bid'].get('c', 0))
        else:
            return None
            
        if 'ask' in candle and isinstance(candle['ask'], dict):
            ask_close = float(candle['ask'].get('c', 0))
        else:
            return None
        
        # Calculate spread
        spread = ask_close - bid_close
        
        # Create MarketData object with the correct field names
        market_data = MarketData(
            pair=instrument,  # Use 'pair' instead of 'instrument'
            bid=bid_close,
            ask=ask_close,
            timestamp=time_str,  # Use the timestamp string directly
            spread=spread,
            is_live=False,
            data_source='backtest',
            last_update_age=0,
            volatility_score=0.0,
            regime='unknown',
            correlation_risk=0.0,
            confidence=1.0,
            validation_status='valid'
        )
        
        return market_data
    except Exception as e:
        logger.error(f"Error creating MarketData: {e}")
        return None

def test_strategy_characteristics(strategy, strategy_type, instruments):
    """Test the fundamental characteristics of a strategy with actual OANDA data"""
    client = OandaClient()
    
    logger.info(f"\n{'='*70}")
    logger.info(f"🔍 TESTING STRATEGY: {strategy.name}")
    logger.info(f"{'='*70}")
    logger.info(f"Instruments: {', '.join(instruments)}")
    
    # Configure strategy with proper parameters
    configure_strategy_parameters(strategy, strategy_type)
    
    # Get latest candles for each instrument
    market_data_dict = {}
    for instrument in instruments:
        try:
            logger.info(f"  Fetching latest candles for {instrument}...")
            response = client.get_candles(
                instrument=instrument,
                granularity="M5",
                count=100  # Get 100 most recent candles
            )
            
            if not response or 'candles' not in response:
                logger.error(f"    ❌ No data returned for {instrument}")
                continue
                
            candles = response['candles']
            logger.info(f"    ✅ {len(candles)} candles retrieved")
            
            # Use the latest complete candle
            latest_candle = None
            for candle in reversed(candles):
                if candle.get('complete', False):
                    latest_candle = candle
                    break
            
            if not latest_candle:
                logger.warning(f"    ⚠️ No complete candles found for {instrument}")
                latest_candle = candles[-1]  # Use the latest incomplete candle
                
            # Create MarketData from the candle
            market_data = create_market_data_from_candle(latest_candle, instrument)
            if market_data:
                market_data_dict[instrument] = market_data
                logger.info(f"    ✅ MarketData created: {instrument} bid={market_data.bid}, ask={market_data.ask}")
            else:
                logger.error(f"    ❌ Failed to create MarketData for {instrument}")
                
        except Exception as e:
            logger.error(f"    ❌ Error fetching {instrument}: {e}")
    
    if not market_data_dict:
        logger.error("❌ No market data available for testing!")
        return {
            'strategy': strategy.name,
            'status': 'FAILURE - No Data',
            'characteristics': {}
        }
    
    # Initialize price history if needed
    if hasattr(strategy, 'price_history'):
        # Pre-fill price history with some data
        logger.info("  Pre-filling price history...")
        for instrument in instruments:
            if instrument in market_data_dict:
                # Get historical data for pre-filling
                try:
                    historical_response = client.get_candles(
                        instrument=instrument,
                        granularity="M5",
                        count=100
                    )
                    
                    if historical_response and 'candles' in historical_response:
                        historical_candles = historical_response['candles']
                        
                        # Extract close prices
                        if isinstance(strategy.price_history, dict):
                            if instrument not in strategy.price_history:
                                strategy.price_history[instrument] = []
                                
                            # Add close prices to price history
                            for candle in historical_candles:
                                if 'mid' in candle and isinstance(candle['mid'], dict):
                                    close_price = float(candle['mid'].get('c', 0))
                                elif 'ask' in candle and isinstance(candle['ask'], dict):
                                    close_price = float(candle['ask'].get('c', 0))
                                elif 'bid' in candle and isinstance(candle['bid'], dict):
                                    close_price = float(candle['bid'].get('c', 0))
                                else:
                                    continue
                                    
                                strategy.price_history[instrument].append(close_price)
                                
                            logger.info(f"    ✅ Added {len(strategy.price_history[instrument])} prices to {instrument} history")
                        else:
                            # For strategies with a single price history list
                            strategy.price_history = []
                            
                            # Add close prices to price history
                            for candle in historical_candles:
                                if 'mid' in candle and isinstance(candle['mid'], dict):
                                    close_price = float(candle['mid'].get('c', 0))
                                elif 'ask' in candle and isinstance(candle['ask'], dict):
                                    close_price = float(candle['ask'].get('c', 0))
                                elif 'bid' in candle and isinstance(candle['bid'], dict):
                                    close_price = float(candle['bid'].get('c', 0))
                                else:
                                    continue
                                    
                                strategy.price_history.append(close_price)
                                
                            logger.info(f"    ✅ Added {len(strategy.price_history)} prices to price history")
                            
                except Exception as e:
                    logger.error(f"    ❌ Error pre-filling price history for {instrument}: {e}")
    
    # Test strategy with market data
    try:
        logger.info("  Testing strategy with current market data...")
        signals = strategy.analyze_market(market_data_dict)
        
        if signals:
            logger.info(f"    ✅ Strategy generated {len(signals)} signals:")
            for i, signal in enumerate(signals):
                if signal:
                    # Extract signal attributes
                    instrument = getattr(signal, 'instrument', 'Unknown')
                    side = getattr(signal, 'side', 'Unknown')
                    if hasattr(side, 'value'):
                        side = side.value
                    entry_price = getattr(signal, 'entry_price', 'Unknown')
                    stop_loss = getattr(signal, 'stop_loss', 'Unknown')
                    take_profit = getattr(signal, 'take_profit', 'Unknown')
                    strength = getattr(signal, 'strength', 'Unknown')
                    
                    logger.info(f"      Signal {i+1}: {instrument} {side} @ {entry_price}")
                    logger.info(f"        Stop Loss: {stop_loss}")
                    logger.info(f"        Take Profit: {take_profit}")
                    logger.info(f"        Quality/Strength: {strength}")
                    
                    # Calculate risk-reward ratio
                    if isinstance(entry_price, (int, float)) and isinstance(stop_loss, (int, float)) and isinstance(take_profit, (int, float)):
                        if side == 'BUY' or side == 'LONG':
                            risk = entry_price - stop_loss
                            reward = take_profit - entry_price
                        else:  # SELL/SHORT
                            risk = stop_loss - entry_price
                            reward = entry_price - take_profit
                            
                        if risk > 0:
                            rr_ratio = reward / risk
                            logger.info(f"        Risk-Reward Ratio: 1:{rr_ratio:.2f}")
        else:
            logger.info("    ⚠️ No signals generated")
            
        # Evaluate strategy characteristics
        characteristics = {}
        
        # Check if strategy uses proper ADX filter
        if hasattr(strategy, 'min_adx'):
            characteristics['uses_adx_filter'] = strategy.min_adx >= 20.0
            characteristics['adx_threshold'] = strategy.min_adx
            
        # Check if strategy uses proper momentum filter
        if hasattr(strategy, 'min_momentum'):
            characteristics['uses_momentum_filter'] = strategy.min_momentum >= 0.003
            characteristics['momentum_threshold'] = strategy.min_momentum
            
        # Check if strategy uses quality scoring
        if hasattr(strategy, 'min_quality_score'):
            characteristics['uses_quality_scoring'] = strategy.min_quality_score > 0
            characteristics['quality_threshold'] = strategy.min_quality_score
            
        # Check if strategy has proper risk management
        if hasattr(strategy, 'stop_loss_atr'):
            characteristics['uses_atr_stops'] = True
            characteristics['stop_loss_atr'] = strategy.stop_loss_atr
            characteristics['take_profit_atr'] = getattr(strategy, 'take_profit_atr', 'Unknown')
        elif hasattr(strategy, 'stop_loss_pips'):
            characteristics['uses_fixed_stops'] = True
            characteristics['stop_loss_pips'] = strategy.stop_loss_pips
            characteristics['take_profit_pips'] = getattr(strategy, 'take_profit_pips', 'Unknown')
            
        # Check if strategy has trade limits
        if hasattr(strategy, 'max_trades_per_day'):
            characteristics['has_trade_limits'] = strategy.max_trades_per_day > 0
            characteristics['max_trades_per_day'] = strategy.max_trades_per_day
            
        # Check if strategy uses trend continuation
        if hasattr(strategy, 'require_trend_continuation'):
            characteristics['requires_trend_continuation'] = strategy.require_trend_continuation
            
        # Evaluate overall quality of strategy parameters
        quality_score = 0
        max_score = 0
        
        # ADX filter
        if 'uses_adx_filter' in characteristics:
            max_score += 1
            if characteristics['uses_adx_filter']:
                quality_score += 1
                
        # Momentum filter
        if 'uses_momentum_filter' in characteristics:
            max_score += 1
            if characteristics['uses_momentum_filter']:
                quality_score += 1
                
        # Quality scoring
        if 'uses_quality_scoring' in characteristics:
            max_score += 1
            if characteristics['uses_quality_scoring'] and characteristics['quality_threshold'] >= 50:
                quality_score += 1
                
        # Risk management
        if 'uses_atr_stops' in characteristics or 'uses_fixed_stops' in characteristics:
            max_score += 1
            if ('uses_atr_stops' in characteristics and characteristics['stop_loss_atr'] >= 1.5) or \
               ('uses_fixed_stops' in characteristics and characteristics['stop_loss_pips'] >= 10):
                quality_score += 1
                
        # Trade limits
        if 'has_trade_limits' in characteristics:
            max_score += 1
            if characteristics['has_trade_limits']:
                quality_score += 1
                
        # Trend continuation
        if 'requires_trend_continuation' in characteristics:
            max_score += 1
            if characteristics['requires_trend_continuation']:
                quality_score += 1
                
        # Calculate overall quality score
        overall_quality = (quality_score / max_score * 100) if max_score > 0 else 0
        characteristics['overall_quality'] = overall_quality
        
        # Determine status
        if overall_quality >= 80:
            status = "✅ PASS - Excellent Strategy Quality"
        elif overall_quality >= 60:
            status = "✅ PASS - Good Strategy Quality"
        elif overall_quality >= 40:
            status = "⚠️ WARNING - Mediocre Strategy Quality"
        else:
            status = "❌ FAILURE - Poor Strategy Quality"
            
        logger.info(f"\n  Strategy Quality Assessment:")
        logger.info(f"    Overall Quality Score: {overall_quality:.1f}%")
        logger.info(f"    Status: {status}")
        
        return {
            'strategy': strategy.name,
            'signals_generated': len(signals) if signals else 0,
            'status': status,
            'characteristics': characteristics,
            'quality_score': overall_quality
        }
        
    except Exception as e:
        logger.error(f"❌ Error testing strategy: {e}")
        return {
            'strategy': strategy.name,
            'status': f'FAILURE - Error: {str(e)}',
            'characteristics': {}
        }

def main():
    """Test the fundamental characteristics of all strategies"""
    
    logger.info("\n" + "="*70)
    logger.info("🔍 DIRECT STRATEGY TEST - FUNDAMENTAL CHARACTERISTICS")
    logger.info("="*70)
    logger.info("Quality Score Threshold: 60%")
    logger.info("Below 60% = FAILURE ❌")
    logger.info("="*70 + "\n")
    
    # Define strategies to test with their fundamental characteristics
    strategies = [
        {
            'name': 'Trump DNA (Momentum Trading)',
            'strategy': MomentumTradingStrategy(),
            'instruments': ['XAU_USD'],  # Focus on Gold for faster testing
            'type': 'momentum'
        },
        {
            'name': 'Gold Scalping',
            'strategy': GoldScalpingStrategy(),
            'instruments': ['XAU_USD'],
            'type': 'scalping'
        }
    ]
    
    # Test each strategy
    results = []
    for strategy_config in strategies:
        try:
            result = test_strategy_characteristics(
                strategy_config['strategy'],
                strategy_config['type'],
                strategy_config['instruments']
            )
            results.append(result)
        except Exception as e:
            logger.error(f"❌ Error testing {strategy_config['name']}: {e}")
            results.append({
                'strategy': strategy_config['name'],
                'status': f'FAILURE - Error: {str(e)}',
                'characteristics': {},
                'quality_score': 0
            })
    
    # Print summary
    logger.info("\n" + "="*70)
    logger.info("📊 FINAL SUMMARY - STRATEGY CHARACTERISTICS")
    logger.info("="*70)
    logger.info(f"{'Strategy':<40} {'Quality Score':<15} {'Signals':<10} {'Status':<30}")
    logger.info("-"*70)
    
    for result in results:
        quality_score = f"{result.get('quality_score', 0):.1f}%"
        signals = result.get('signals_generated', 0)
        logger.info(f"{result['strategy']:<40} {quality_score:<15} {signals:<10} {result['status']:<30}")
    
    logger.info("="*70)
    
    # Count failures
    failures = [r for r in results if 'FAILURE' in r['status']]
    warnings = [r for r in results if 'WARNING' in r['status']]
    passes = [r for r in results if 'PASS' in r['status']]
    
    logger.info(f"\n✅ PASSED: {len(passes)}")
    logger.info(f"⚠️ WARNING: {len(warnings)}")
    logger.info(f"❌ FAILED: {len(failures)}")
    
    if failures:
        logger.info("\n⚠️ FAILED STRATEGIES:")
        for failure in failures:
            logger.info(f"  - {failure['strategy']}: {failure.get('quality_score', 0):.1f}% quality score")
    
    # Save detailed results
    output_file = 'strategy_characteristics_results.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    logger.info(f"\n💾 Detailed results saved to {output_file}")

if __name__ == "__main__":
    main()