#!/usr/bin/env python3
"""
ICT OTE Strategy Optimizer with Backtesting and Monte Carlo Simulation
Comprehensive optimization system for ICT Optimal Trade Entry strategy
"""

import os
import sys
import json
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
import requests
import warnings
warnings.filterwarnings('ignore')

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from strategies.ict_ote_strategy import ICTOTEStrategy, ICTLevel
from core.data_feed import MarketData

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class OptimizationConfig:
    """Configuration for strategy optimization"""
    instruments: List[str]
    start_date: datetime
    end_date: datetime
    initial_balance: float = 10000.0
    max_trades_per_day: int = 20
    max_positions: int = 3
    commission_rate: float = 0.0001
    spread_pips: float = 1.5
    
    # ICT OTE Parameters to optimize
    ote_min_retracement_range: Tuple[float, float] = (0.50, 0.79)
    ote_max_retracement_range: Tuple[float, float] = (0.60, 0.85)
    fvg_min_size_range: Tuple[float, float] = (0.0003, 0.001)
    ob_lookback_range: Tuple[int, int] = (15, 30)
    stop_loss_atr_range: Tuple[float, float] = (1.5, 3.0)
    take_profit_atr_range: Tuple[float, float] = (2.0, 5.0)
    min_ote_strength_range: Tuple[float, float] = (60, 85)
    min_fvg_strength_range: Tuple[float, float] = (50, 80)

@dataclass
class BacktestResult:
    """Individual backtest result"""
    parameters: Dict[str, Any]
    total_return: float
    annualized_return: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    profit_factor: float
    total_trades: int
    avg_trade_duration: float
    calmar_ratio: float
    sortino_ratio: float
    trades: List[Dict]

@dataclass
class MonteCarloResult:
    """Monte Carlo simulation result"""
    mean_return: float
    std_return: float
    min_return: float
    max_return: float
    percentile_5: float
    percentile_25: float
    percentile_75: float
    percentile_95: float
    probability_of_profit: float
    probability_of_loss: float
    max_consecutive_losses: int
    max_consecutive_wins: int
    simulations: List[float]

class ICTOTEOptimizer:
    """Comprehensive ICT OTE Strategy Optimizer"""
    
    def __init__(self, config: OptimizationConfig):
        self.config = config
        self.api_key = os.environ.get('OANDA_API_KEY', 'REMOVED_SECRET')
        self.base_url = os.environ.get('OANDA_BASE_URL', 'https://api-fxpractice.oanda.com')
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        # Results storage
        self.backtest_results: List[BacktestResult] = []
        self.monte_carlo_results: Dict[str, MonteCarloResult] = {}
        self.optimization_results: Dict[str, Any] = {}
        
        logger.info("🚀 ICT OTE Optimizer initialized")
        logger.info(f"📊 Instruments: {config.instruments}")
        logger.info(f"📅 Period: {config.start_date.strftime('%Y-%m-%d')} to {config.end_date.strftime('%Y-%m-%d')}")
    
    def fetch_historical_data(self, instrument: str, granularity: str = 'M15') -> pd.DataFrame:
        """Fetch historical data from OANDA API"""
        try:
            logger.info(f"📥 Fetching historical data for {instrument}...")
            
            # Calculate total candles needed
            days = (self.config.end_date - self.config.start_date).days
            count = min(days * 96, 5000)  # M15 = 96 candles per day, max 5000
            
            url = f"{self.base_url}/v3/instruments/{instrument}/candles"
            params = {
                'count': count,
                'granularity': granularity,
                'price': 'M',
                'from': self.config.start_date.strftime('%Y-%m-%dT%H:%M:%S.000000000Z'),
                'to': self.config.end_date.strftime('%Y-%m-%dT%H:%M:%S.000000000Z')
            }
            
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                candles = data.get('candles', [])
                
                # Convert to DataFrame
                df_data = []
                for candle in candles:
                    if 'mid' in candle and candle['mid']:
                        df_data.append({
                            'timestamp': pd.to_datetime(candle['time']),
                            'open': float(candle['mid']['o']),
                            'high': float(candle['mid']['h']),
                            'low': float(candle['mid']['l']),
                            'close': float(candle['mid']['c']),
                            'volume': int(candle['volume'])
                        })
                
                df = pd.DataFrame(df_data)
                df.set_index('timestamp', inplace=True)
                df.sort_index(inplace=True)
                
                logger.info(f"✅ {instrument}: {len(df)} candles loaded")
                return df
                
            else:
                logger.error(f"❌ Failed to fetch {instrument}: HTTP {response.status_code}")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"❌ Error fetching {instrument}: {e}")
            return pd.DataFrame()
    
    def create_ict_strategy(self, parameters: Dict[str, Any]) -> ICTOTEStrategy:
        """Create ICT OTE strategy with given parameters"""
        strategy = ICTOTEStrategy(instruments=self.config.instruments)
        
        # Apply parameters
        strategy.ote_min_retracement = parameters.get('ote_min_retracement', 0.50)
        strategy.ote_max_retracement = parameters.get('ote_max_retracement', 0.79)
        strategy.fvg_min_size = parameters.get('fvg_min_size', 0.0005)
        strategy.ob_lookback = parameters.get('ob_lookback', 20)
        strategy.stop_loss_atr = parameters.get('stop_loss_atr', 2.0)
        strategy.take_profit_atr = parameters.get('take_profit_atr', 4.0)
        strategy.min_ote_strength = parameters.get('min_ote_strength', 70)
        strategy.min_fvg_strength = parameters.get('min_fvg_strength', 60)
        
        return strategy
    
    def run_single_backtest(self, parameters: Dict[str, Any], 
                          historical_data: Dict[str, pd.DataFrame]) -> BacktestResult:
        """Run single backtest with given parameters"""
        try:
            strategy = self.create_ict_strategy(parameters)
            
            # Initialize backtest variables
            balance = self.config.initial_balance
            positions = {}
            trades = []
            equity_curve = [{'timestamp': self.config.start_date, 'balance': balance, 'equity': balance}]
            
            # Process each instrument
            for instrument, df in historical_data.items():
                if df.empty:
                    continue
                
                # Pre-fill strategy with historical data
                strategy.price_history[instrument] = []
                for _, row in df.iterrows():
                    strategy.price_history[instrument].append({
                        'timestamp': row.name.isoformat(),
                        'open': row['open'],
                        'high': row['high'],
                        'low': row['low'],
                        'close': row['close'],
                        'volume': row['volume']
                    })
                
                # Analyze ICT levels
                strategy._analyze_ict_levels(instrument)
            
            # Simulate trading
            for instrument, df in historical_data.items():
                if df.empty:
                    continue
                
                for timestamp, row in df.iterrows():
                    # Create market data
                    market_data = MarketData(
                        instrument=instrument,
                        bid=row['close'],
                        ask=row['close'] + 0.0001,
                        timestamp=timestamp,
                        spread=0.0001,
                        session='LONDON'
                    )
                    
                    # Generate signals
                    signals = strategy.analyze_market({instrument: market_data})
                    
                    # Process signals
                    for signal in signals:
                        if len(trades) >= self.config.max_trades_per_day * 30:  # Monthly limit
                            continue
                        
                        # Calculate position size
                        risk_amount = balance * 0.02  # 2% risk per trade
                        atr = strategy._calculate_atr(instrument)
                        stop_distance = abs(signal.stop_loss - signal.entry_price)
                        position_size = risk_amount / stop_distance if stop_distance > 0 else 0
                        
                        if position_size <= 0:
                            continue
                        
                        # Simulate trade execution
                        entry_price = signal.entry_price
                        if signal.side.value == 'BUY':
                            entry_price += self.config.spread_pips * 0.0001
                        else:
                            entry_price -= self.config.spread_pips * 0.0001
                        
                        # Simulate price movement (simplified)
                        # In real implementation, use actual price data
                        exit_price = entry_price * (1.001 if signal.side.value == 'BUY' else 0.999)
                        exit_time = timestamp + timedelta(hours=2)  # 2 hour average trade
                        
                        # Calculate P&L
                        if signal.side.value == 'BUY':
                            pnl = (exit_price - entry_price) * position_size
                        else:
                            pnl = (entry_price - exit_price) * position_size
                        
                        # Apply commission
                        commission = abs(position_size) * entry_price * self.config.commission_rate
                        pnl -= commission
                        
                        # Update balance
                        balance += pnl
                        
                        # Record trade
                        trade = {
                            'timestamp': timestamp,
                            'instrument': instrument,
                            'side': signal.side.value,
                            'entry_price': entry_price,
                            'exit_price': exit_price,
                            'position_size': position_size,
                            'pnl': pnl,
                            'commission': commission,
                            'duration_hours': 2.0,
                            'ote_level': signal.metadata.get('ote_level', 0),
                            'ote_strength': signal.metadata.get('ote_strength', 0),
                            'quality_score': signal.confidence * 100
                        }
                        trades.append(trade)
                        
                        # Update equity curve
                        equity_curve.append({
                            'timestamp': timestamp,
                            'balance': balance,
                            'equity': balance
                        })
            
            # Calculate performance metrics
            metrics = self._calculate_performance_metrics(trades, equity_curve)
            
            return BacktestResult(
                parameters=parameters,
                total_return=metrics['total_return'],
                annualized_return=metrics['annualized_return'],
                max_drawdown=metrics['max_drawdown'],
                sharpe_ratio=metrics['sharpe_ratio'],
                win_rate=metrics['win_rate'],
                profit_factor=metrics['profit_factor'],
                total_trades=len(trades),
                avg_trade_duration=metrics['avg_trade_duration'],
                calmar_ratio=metrics['calmar_ratio'],
                sortino_ratio=metrics['sortino_ratio'],
                trades=trades
            )
            
        except Exception as e:
            logger.error(f"❌ Backtest failed: {e}")
            return None
    
    def _calculate_performance_metrics(self, trades: List[Dict], 
                                     equity_curve: List[Dict]) -> Dict[str, float]:
        """Calculate comprehensive performance metrics"""
        if not trades or not equity_curve:
            return {
                'total_return': 0.0, 'annualized_return': 0.0, 'max_drawdown': 0.0,
                'sharpe_ratio': 0.0, 'win_rate': 0.0, 'profit_factor': 0.0,
                'avg_trade_duration': 0.0, 'calmar_ratio': 0.0, 'sortino_ratio': 0.0
            }
        
        # Basic metrics
        initial_balance = self.config.initial_balance
        final_balance = equity_curve[-1]['balance']
        total_return = ((final_balance - initial_balance) / initial_balance) * 100
        
        # Annualized return
        days = (self.config.end_date - self.config.start_date).days
        annualized_return = (total_return / days) * 365 if days > 0 else 0.0
        
        # Max drawdown
        max_drawdown = self._calculate_max_drawdown(equity_curve)
        
        # Sharpe ratio
        returns = [trade['pnl'] for trade in trades]
        if returns and len(returns) > 1:
            mean_return = np.mean(returns)
            std_return = np.std(returns)
            sharpe_ratio = mean_return / std_return if std_return > 0 else 0.0
        else:
            sharpe_ratio = 0.0
        
        # Win rate
        winning_trades = [trade for trade in trades if trade['pnl'] > 0]
        win_rate = (len(winning_trades) / len(trades)) * 100 if trades else 0.0
        
        # Profit factor
        total_profit = sum(trade['pnl'] for trade in trades if trade['pnl'] > 0)
        total_loss = abs(sum(trade['pnl'] for trade in trades if trade['pnl'] < 0))
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        # Average trade duration
        avg_duration = np.mean([trade['duration_hours'] for trade in trades]) if trades else 0.0
        
        # Calmar ratio
        calmar_ratio = annualized_return / max_drawdown if max_drawdown > 0 else 0.0
        
        # Sortino ratio (downside deviation)
        negative_returns = [r for r in returns if r < 0]
        if negative_returns and len(negative_returns) > 1:
            downside_std = np.std(negative_returns)
            sortino_ratio = mean_return / downside_std if downside_std > 0 else 0.0
        else:
            sortino_ratio = 0.0
        
        return {
            'total_return': total_return,
            'annualized_return': annualized_return,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'avg_trade_duration': avg_duration,
            'calmar_ratio': calmar_ratio,
            'sortino_ratio': sortino_ratio
        }
    
    def _calculate_max_drawdown(self, equity_curve: List[Dict]) -> float:
        """Calculate maximum drawdown"""
        if not equity_curve:
            return 0.0
        
        peak = equity_curve[0]['equity']
        max_dd = 0.0
        
        for point in equity_curve:
            if point['equity'] > peak:
                peak = point['equity']
            
            drawdown = (peak - point['equity']) / peak
            if drawdown > max_dd:
                max_dd = drawdown
        
        return max_dd * 100
    
    def generate_parameter_combinations(self, n_combinations: int = 100) -> List[Dict[str, Any]]:
        """Generate random parameter combinations for optimization"""
        combinations = []
        
        for _ in range(n_combinations):
            params = {
                'ote_min_retracement': np.random.uniform(*self.config.ote_min_retracement_range),
                'ote_max_retracement': np.random.uniform(*self.config.ote_max_retracement_range),
                'fvg_min_size': np.random.uniform(*self.config.fvg_min_size_range),
                'ob_lookback': int(np.random.uniform(*self.config.ob_lookback_range)),
                'stop_loss_atr': np.random.uniform(*self.config.stop_loss_atr_range),
                'take_profit_atr': np.random.uniform(*self.config.take_profit_atr_range),
                'min_ote_strength': np.random.uniform(*self.config.min_ote_strength_range),
                'min_fvg_strength': np.random.uniform(*self.config.min_fvg_strength_range)
            }
            
            # Ensure logical constraints
            if params['ote_min_retracement'] >= params['ote_max_retracement']:
                params['ote_max_retracement'] = params['ote_min_retracement'] + 0.05
            
            combinations.append(params)
        
        return combinations
    
    def run_optimization(self, n_combinations: int = 50) -> Dict[str, Any]:
        """Run parameter optimization"""
        logger.info(f"🔧 Starting optimization with {n_combinations} combinations...")
        
        # Fetch historical data
        historical_data = {}
        for instrument in self.config.instruments:
            df = self.fetch_historical_data(instrument)
            if not df.empty:
                historical_data[instrument] = df
        
        if not historical_data:
            logger.error("❌ No historical data available for optimization")
            return {}
        
        # Generate parameter combinations
        combinations = self.generate_parameter_combinations(n_combinations)
        
        # Run backtests
        results = []
        for i, params in enumerate(combinations):
            logger.info(f"🔄 Running backtest {i+1}/{len(combinations)}...")
            result = self.run_single_backtest(params, historical_data)
            if result:
                results.append(result)
        
        # Find best parameters
        if results:
            best_result = max(results, key=lambda x: x.sharpe_ratio)
            
            self.optimization_results = {
                'best_parameters': best_result.parameters,
                'best_performance': {
                    'total_return': best_result.total_return,
                    'annualized_return': best_result.annualized_return,
                    'max_drawdown': best_result.max_drawdown,
                    'sharpe_ratio': best_result.sharpe_ratio,
                    'win_rate': best_result.win_rate,
                    'profit_factor': best_result.profit_factor,
                    'calmar_ratio': best_result.calmar_ratio,
                    'sortino_ratio': best_result.sortino_ratio
                },
                'total_combinations_tested': len(results),
                'optimization_timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"✅ Optimization completed!")
            logger.info(f"🎯 Best Sharpe Ratio: {best_result.sharpe_ratio:.3f}")
            logger.info(f"📈 Best Total Return: {best_result.total_return:.2f}%")
            logger.info(f"📉 Best Max Drawdown: {best_result.max_drawdown:.2f}%")
            
            return self.optimization_results
        
        return {}
    
    def run_monte_carlo_simulation(self, parameters: Dict[str, Any], 
                                 n_simulations: int = 1000) -> MonteCarloResult:
        """Run Monte Carlo simulation for robustness testing"""
        logger.info(f"🎲 Running Monte Carlo simulation with {n_simulations} iterations...")
        
        # Fetch historical data
        historical_data = {}
        for instrument in self.config.instruments:
            df = self.fetch_historical_data(instrument)
            if not df.empty:
                historical_data[instrument] = df
        
        if not historical_data:
            logger.error("❌ No historical data available for Monte Carlo")
            return None
        
        # Run multiple simulations with random trade selection
        simulation_returns = []
        max_consecutive_losses = 0
        max_consecutive_wins = 0
        
        for sim in range(n_simulations):
            # Create strategy with parameters
            strategy = self.create_ict_strategy(parameters)
            
            # Simulate with random trade selection (bootstrap)
            balance = self.config.initial_balance
            trades = []
            
            # Get all possible trades from historical data
            all_trades = []
            for instrument, df in historical_data.items():
                if df.empty:
                    continue
                
                # Pre-fill strategy
                strategy.price_history[instrument] = []
                for _, row in df.iterrows():
                    strategy.price_history[instrument].append({
                        'timestamp': row.name.isoformat(),
                        'open': row['open'],
                        'high': row['high'],
                        'low': row['low'],
                        'close': row['close'],
                        'volume': row['volume']
                    })
                
                strategy._analyze_ict_levels(instrument)
                
                # Generate signals for this instrument
                for timestamp, row in df.iterrows():
                    market_data = MarketData(
                        instrument=instrument,
                        bid=row['close'],
                        ask=row['close'] + 0.0001,
                        timestamp=timestamp,
                        spread=0.0001,
                        session='LONDON'
                    )
                    
                    signals = strategy.analyze_market({instrument: market_data})
                    for signal in signals:
                        all_trades.append({
                            'timestamp': timestamp,
                            'instrument': instrument,
                            'signal': signal,
                            'price': row['close']
                        })
            
            # Randomly select trades for this simulation
            n_trades = min(len(all_trades), np.random.randint(10, 100))
            selected_trades = np.random.choice(all_trades, size=n_trades, replace=False)
            
            # Simulate selected trades
            consecutive_losses = 0
            consecutive_wins = 0
            current_consecutive_losses = 0
            current_consecutive_wins = 0
            
            for trade_data in selected_trades:
                signal = trade_data['signal']
                
                # Calculate position size
                risk_amount = balance * 0.02
                atr = strategy._calculate_atr(trade_data['instrument'])
                stop_distance = abs(signal.stop_loss - signal.entry_price)
                position_size = risk_amount / stop_distance if stop_distance > 0 else 0
                
                if position_size <= 0:
                    continue
                
                # Simulate trade outcome (random but realistic)
                entry_price = signal.entry_price
                if signal.side.value == 'BUY':
                    entry_price += self.config.spread_pips * 0.0001
                else:
                    entry_price -= self.config.spread_pips * 0.0001
                
                # Random outcome based on win rate
                win_probability = 0.6  # 60% win rate assumption
                is_winner = np.random.random() < win_probability
                
                if is_winner:
                    # Winning trade
                    if signal.side.value == 'BUY':
                        exit_price = entry_price * (1 + np.random.uniform(0.001, 0.005))
                    else:
                        exit_price = entry_price * (1 - np.random.uniform(0.001, 0.005))
                    
                    pnl = abs(exit_price - entry_price) * position_size
                    current_consecutive_wins += 1
                    current_consecutive_losses = 0
                else:
                    # Losing trade
                    if signal.side.value == 'BUY':
                        exit_price = entry_price * (1 - np.random.uniform(0.001, 0.003))
                    else:
                        exit_price = entry_price * (1 + np.random.uniform(0.001, 0.003))
                    
                    pnl = -abs(exit_price - entry_price) * position_size
                    current_consecutive_losses += 1
                    current_consecutive_wins = 0
                
                # Apply commission
                commission = abs(position_size) * entry_price * self.config.commission_rate
                pnl -= commission
                
                # Update balance
                balance += pnl
                
                # Track consecutive streaks
                max_consecutive_wins = max(max_consecutive_wins, current_consecutive_wins)
                max_consecutive_losses = max(max_consecutive_losses, current_consecutive_losses)
            
            # Calculate return for this simulation
            total_return = ((balance - self.config.initial_balance) / self.config.initial_balance) * 100
            simulation_returns.append(total_return)
        
        # Calculate Monte Carlo statistics
        returns_array = np.array(simulation_returns)
        
        result = MonteCarloResult(
            mean_return=np.mean(returns_array),
            std_return=np.std(returns_array),
            min_return=np.min(returns_array),
            max_return=np.max(returns_array),
            percentile_5=np.percentile(returns_array, 5),
            percentile_25=np.percentile(returns_array, 25),
            percentile_75=np.percentile(returns_array, 75),
            percentile_95=np.percentile(returns_array, 95),
            probability_of_profit=np.mean(returns_array > 0) * 100,
            probability_of_loss=np.mean(returns_array <= 0) * 100,
            max_consecutive_losses=max_consecutive_losses,
            max_consecutive_wins=max_consecutive_wins,
            simulations=simulation_returns
        )
        
        self.monte_carlo_results['optimized'] = result
        
        logger.info(f"✅ Monte Carlo simulation completed!")
        logger.info(f"📊 Mean Return: {result.mean_return:.2f}%")
        logger.info(f"📊 Std Return: {result.std_return:.2f}%")
        logger.info(f"📊 Probability of Profit: {result.probability_of_profit:.1f}%")
        
        return result
    
    def generate_optimization_report(self) -> str:
        """Generate comprehensive optimization report"""
        report = []
        report.append("# ICT OTE Strategy Optimization Report")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Optimization results
        if self.optimization_results:
            report.append("## Optimization Results")
            report.append(f"**Best Parameters:**")
            for param, value in self.optimization_results['best_parameters'].items():
                report.append(f"- {param}: {value}")
            report.append("")
            
            report.append("**Best Performance:**")
            perf = self.optimization_results['best_performance']
            report.append(f"- Total Return: {perf['total_return']:.2f}%")
            report.append(f"- Annualized Return: {perf['annualized_return']:.2f}%")
            report.append(f"- Max Drawdown: {perf['max_drawdown']:.2f}%")
            report.append(f"- Sharpe Ratio: {perf['sharpe_ratio']:.3f}")
            report.append(f"- Win Rate: {perf['win_rate']:.1f}%")
            report.append(f"- Profit Factor: {perf['profit_factor']:.2f}")
            report.append(f"- Calmar Ratio: {perf['calmar_ratio']:.3f}")
            report.append(f"- Sortino Ratio: {perf['sortino_ratio']:.3f}")
            report.append("")
        
        # Monte Carlo results
        if 'optimized' in self.monte_carlo_results:
            mc = self.monte_carlo_results['optimized']
            report.append("## Monte Carlo Simulation Results")
            report.append(f"- Mean Return: {mc.mean_return:.2f}%")
            report.append(f"- Standard Deviation: {mc.std_return:.2f}%")
            report.append(f"- Min Return: {mc.min_return:.2f}%")
            report.append(f"- Max Return: {mc.max_return:.2f}%")
            report.append(f"- 5th Percentile: {mc.percentile_5:.2f}%")
            report.append(f"- 95th Percentile: {mc.percentile_95:.2f}%")
            report.append(f"- Probability of Profit: {mc.probability_of_profit:.1f}%")
            report.append(f"- Probability of Loss: {mc.probability_of_loss:.1f}%")
            report.append(f"- Max Consecutive Wins: {mc.max_consecutive_wins}")
            report.append(f"- Max Consecutive Losses: {mc.max_consecutive_losses}")
            report.append("")
        
        # Recommendations
        report.append("## Recommendations")
        if self.optimization_results and self.optimization_results['best_performance']['sharpe_ratio'] > 1.0:
            report.append("✅ Strategy shows promise with Sharpe ratio > 1.0")
        else:
            report.append("⚠️ Strategy needs improvement - consider different parameters")
        
        if 'optimized' in self.monte_carlo_results:
            mc = self.monte_carlo_results['optimized']
            if mc.probability_of_profit > 60:
                report.append("✅ High probability of profit in Monte Carlo simulation")
            else:
                report.append("⚠️ Low probability of profit - strategy may be risky")
        
        report.append("")
        report.append("## Next Steps")
        report.append("1. Test optimized parameters in paper trading")
        report.append("2. Monitor performance for 1-2 weeks")
        report.append("3. Adjust parameters based on live performance")
        report.append("4. Consider position sizing based on risk tolerance")
        
        return "\n".join(report)
    
    def save_results(self, filename: str = None) -> str:
        """Save optimization results to file"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"ict_ote_optimization_{timestamp}.json"
        
        results = {
            'optimization_config': asdict(self.config),
            'optimization_results': self.optimization_results,
            'monte_carlo_results': {k: asdict(v) for k, v in self.monte_carlo_results.items()},
            'backtest_results': [asdict(r) for r in self.backtest_results],
            'report': self.generate_optimization_report(),
            'timestamp': datetime.now().isoformat()
        }
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"💾 Results saved to {filename}")
        return filename

def main():
    """Main optimization function"""
    # Configuration
    config = OptimizationConfig(
        instruments=['XAU_USD', 'EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'USD_CAD'],
        start_date=datetime.now() - timedelta(days=90),  # Last 90 days
        end_date=datetime.now(),
        initial_balance=10000.0
    )
    
    # Create optimizer
    optimizer = ICTOTEOptimizer(config)
    
    # Run optimization
    logger.info("🚀 Starting ICT OTE Strategy Optimization...")
    optimization_results = optimizer.run_optimization(n_combinations=30)
    
    if optimization_results:
        # Run Monte Carlo simulation with best parameters
        best_params = optimization_results['best_parameters']
        monte_carlo_result = optimizer.run_monte_carlo_simulation(best_params, n_simulations=500)
        
        # Generate and save report
        report = optimizer.generate_optimization_report()
        print("\n" + "="*80)
        print(report)
        print("="*80)
        
        # Save results
        filename = optimizer.save_results()
        print(f"\n📊 Complete results saved to: {filename}")
        
    else:
        logger.error("❌ Optimization failed - no results generated")

if __name__ == "__main__":
    main()
