#!/usr/bin/env python3
"""
ICT OTE Strategy Monte Carlo Simulator
Comprehensive Monte Carlo simulation for ICT Optimal Trade Entry strategy robustness testing
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
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
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
class MonteCarloConfig:
    """Monte Carlo simulation configuration"""
    n_simulations: int = 1000
    confidence_levels: List[float] = None
    bootstrap_samples: int = 100
    random_seed: int = 42
    max_trades_per_simulation: int = 100
    min_trades_per_simulation: int = 10
    
    def __post_init__(self):
        if self.confidence_levels is None:
            self.confidence_levels = [0.05, 0.25, 0.5, 0.75, 0.95]

@dataclass
class MonteCarloMetrics:
    """Monte Carlo simulation metrics"""
    mean_return: float
    median_return: float
    std_return: float
    min_return: float
    max_return: float
    skewness: float
    kurtosis: float
    percentiles: Dict[float, float]
    confidence_intervals: Dict[float, Tuple[float, float]]
    probability_of_profit: float
    probability_of_loss: float
    probability_of_ruin: float
    expected_value: float
    value_at_risk: float
    conditional_value_at_risk: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    max_drawdown_stats: Dict[str, float]
    consecutive_losses_stats: Dict[str, float]
    consecutive_wins_stats: Dict[str, float]
    recovery_time_stats: Dict[str, float]

class ICTOTEMonteCarlo:
    """Comprehensive Monte Carlo Simulator for ICT OTE Strategy"""
    
    def __init__(self, config: MonteCarloConfig):
        self.config = config
        np.random.seed(config.random_seed)
        
        # Results storage
        self.simulation_results: List[Dict] = []
        self.metrics: Optional[MonteCarloMetrics] = None
        
        logger.info("🎲 ICT OTE Monte Carlo Simulator initialized")
        logger.info(f"📊 Simulations: {config.n_simulations}")
        logger.info(f"🎯 Confidence Levels: {config.confidence_levels}")
    
    def run_simulation(self, strategy_parameters: Dict[str, Any], 
                      historical_trades: List[Dict] = None) -> MonteCarloMetrics:
        """Run comprehensive Monte Carlo simulation"""
        try:
            logger.info(f"🎲 Starting Monte Carlo simulation with {self.config.n_simulations} iterations...")
            
            # Generate simulation results
            self.simulation_results = []
            
            for sim in range(self.config.n_simulations):
                if sim % 100 == 0:
                    logger.info(f"🔄 Simulation {sim}/{self.config.n_simulations}")
                
                # Run single simulation
                result = self._run_single_simulation(strategy_parameters, historical_trades)
                if result:
                    self.simulation_results.append(result)
            
            # Calculate metrics
            self.metrics = self._calculate_metrics()
            
            logger.info(f"✅ Monte Carlo simulation completed: {len(self.simulation_results)} successful simulations")
            logger.info(f"📊 Mean Return: {self.metrics.mean_return:.2f}%")
            logger.info(f"📊 Probability of Profit: {self.metrics.probability_of_profit:.1f}%")
            
            return self.metrics
            
        except Exception as e:
            logger.error(f"❌ Monte Carlo simulation failed: {e}")
            return None
    
    def _run_single_simulation(self, strategy_parameters: Dict[str, Any], 
                              historical_trades: List[Dict] = None) -> Optional[Dict]:
        """Run single Monte Carlo simulation"""
        try:
            # Initialize simulation
            initial_balance = 10000.0
            balance = initial_balance
            trades = []
            equity_curve = [initial_balance]
            max_balance = initial_balance
            max_drawdown = 0.0
            
            # Generate trades for this simulation
            if historical_trades:
                # Use bootstrap sampling from historical trades
                n_trades = np.random.randint(
                    self.config.min_trades_per_simulation,
                    min(len(historical_trades), self.config.max_trades_per_simulation)
                )
                selected_trades = np.random.choice(historical_trades, size=n_trades, replace=True)
            else:
                # Generate synthetic trades based on strategy parameters
                selected_trades = self._generate_synthetic_trades(strategy_parameters)
            
            # Process trades
            consecutive_losses = 0
            consecutive_wins = 0
            max_consecutive_losses = 0
            max_consecutive_wins = 0
            
            for trade_data in selected_trades:
                # Calculate position size (2% risk per trade)
                risk_amount = balance * 0.02
                stop_distance = abs(trade_data.get('stop_loss', 0.001))
                position_size = risk_amount / stop_distance if stop_distance > 0 else 0
                
                if position_size <= 0:
                    continue
                
                # Simulate trade outcome
                win_probability = self._calculate_win_probability(trade_data, strategy_parameters)
                is_winner = np.random.random() < win_probability
                
                if is_winner:
                    # Winning trade
                    profit_factor = np.random.uniform(1.5, 3.0)  # 1.5-3.0 R:R
                    pnl = stop_distance * profit_factor * position_size
                    consecutive_wins += 1
                    consecutive_losses = 0
                    max_consecutive_wins = max(max_consecutive_wins, consecutive_wins)
                else:
                    # Losing trade
                    pnl = -stop_distance * position_size
                    consecutive_losses += 1
                    consecutive_wins = 0
                    max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
                
                # Apply commission
                commission = abs(position_size) * 0.0001
                pnl -= commission
                
                # Update balance
                balance += pnl
                equity_curve.append(balance)
                
                # Track max drawdown
                if balance > max_balance:
                    max_balance = balance
                
                current_drawdown = ((max_balance - balance) / max_balance) * 100
                max_drawdown = max(max_drawdown, current_drawdown)
                
                # Record trade
                trades.append({
                    'pnl': pnl,
                    'is_winner': is_winner,
                    'position_size': position_size,
                    'consecutive_losses': consecutive_losses,
                    'consecutive_wins': consecutive_wins
                })
                
                # Check for ruin (50% drawdown)
                if current_drawdown >= 50:
                    break
            
            # Calculate final metrics
            total_return = ((balance - initial_balance) / initial_balance) * 100
            
            # Calculate Sharpe ratio
            if len(trades) > 1:
                returns = [trade['pnl'] for trade in trades]
                mean_return = np.mean(returns)
                std_return = np.std(returns)
                sharpe_ratio = mean_return / std_return if std_return > 0 else 0.0
            else:
                sharpe_ratio = 0.0
            
            # Calculate Sortino ratio
            negative_returns = [r for r in [trade['pnl'] for trade in trades] if r < 0]
            if negative_returns and len(negative_returns) > 1:
                downside_std = np.std(negative_returns)
                sortino_ratio = mean_return / downside_std if downside_std > 0 else 0.0
            else:
                sortino_ratio = 0.0
            
            # Calculate Calmar ratio
            calmar_ratio = total_return / max_drawdown if max_drawdown > 0 else 0.0
            
            return {
                'simulation_id': len(self.simulation_results),
                'total_return': total_return,
                'final_balance': balance,
                'max_drawdown': max_drawdown,
                'sharpe_ratio': sharpe_ratio,
                'sortino_ratio': sortino_ratio,
                'calmar_ratio': calmar_ratio,
                'total_trades': len(trades),
                'winning_trades': sum(1 for t in trades if t['is_winner']),
                'max_consecutive_losses': max_consecutive_losses,
                'max_consecutive_wins': max_consecutive_wins,
                'equity_curve': equity_curve,
                'trades': trades
            }
            
        except Exception as e:
            logger.error(f"❌ Single simulation failed: {e}")
            return None
    
    def _generate_synthetic_trades(self, strategy_parameters: Dict[str, Any]) -> List[Dict]:
        """Generate synthetic trades based on strategy parameters"""
        try:
            n_trades = np.random.randint(
                self.config.min_trades_per_simulation,
                self.config.max_trades_per_simulation
            )
            
            trades = []
            for _ in range(n_trades):
                # Generate trade characteristics
                ote_strength = np.random.uniform(50, 100)
                quality_score = np.random.uniform(60, 95)
                
                # Calculate win probability based on quality
                base_win_rate = 0.5
                quality_bonus = (quality_score - 50) / 100 * 0.3  # Up to 30% bonus
                win_probability = min(0.8, base_win_rate + quality_bonus)
                
                # Generate stop loss distance
                stop_loss = np.random.uniform(0.001, 0.005)  # 10-50 pips
                
                trades.append({
                    'ote_strength': ote_strength,
                    'quality_score': quality_score,
                    'win_probability': win_probability,
                    'stop_loss': stop_loss,
                    'side': np.random.choice(['BUY', 'SELL'])
                })
            
            return trades
            
        except Exception as e:
            logger.error(f"❌ Error generating synthetic trades: {e}")
            return []
    
    def _calculate_win_probability(self, trade_data: Dict, strategy_parameters: Dict[str, Any]) -> float:
        """Calculate win probability for a trade based on its characteristics"""
        try:
            base_win_rate = 0.5
            
            # Quality score bonus
            quality_score = trade_data.get('quality_score', 50)
            quality_bonus = (quality_score - 50) / 100 * 0.3
            
            # OTE strength bonus
            ote_strength = trade_data.get('ote_strength', 50)
            ote_bonus = (ote_strength - 50) / 100 * 0.2
            
            # Strategy parameter bonus
            min_ote_strength = strategy_parameters.get('min_ote_strength', 70)
            if ote_strength >= min_ote_strength:
                strategy_bonus = 0.1
            else:
                strategy_bonus = -0.1
            
            # Calculate final win probability
            win_probability = base_win_rate + quality_bonus + ote_bonus + strategy_bonus
            
            # Ensure reasonable bounds
            return max(0.1, min(0.9, win_probability))
            
        except Exception as e:
            logger.error(f"❌ Error calculating win probability: {e}")
            return 0.5
    
    def _calculate_metrics(self) -> MonteCarloMetrics:
        """Calculate comprehensive Monte Carlo metrics"""
        try:
            if not self.simulation_results:
                return None
            
            # Extract returns
            returns = [result['total_return'] for result in self.simulation_results]
            returns_array = np.array(returns)
            
            # Basic statistics
            mean_return = np.mean(returns_array)
            median_return = np.median(returns_array)
            std_return = np.std(returns_array)
            min_return = np.min(returns_array)
            max_return = np.max(returns_array)
            
            # Higher moments
            skewness = stats.skew(returns_array)
            kurtosis = stats.kurtosis(returns_array)
            
            # Percentiles
            percentiles = {}
            for level in self.config.confidence_levels:
                percentiles[level] = np.percentile(returns_array, level * 100)
            
            # Confidence intervals
            confidence_intervals = {}
            for level in self.config.confidence_levels:
                alpha = 1 - level
                lower = np.percentile(returns_array, (alpha / 2) * 100)
                upper = np.percentile(returns_array, (1 - alpha / 2) * 100)
                confidence_intervals[level] = (lower, upper)
            
            # Probability metrics
            probability_of_profit = np.mean(returns_array > 0) * 100
            probability_of_loss = np.mean(returns_array <= 0) * 100
            probability_of_ruin = np.mean(returns_array < -50) * 100  # 50% loss
            
            # Risk metrics
            expected_value = mean_return
            value_at_risk = np.percentile(returns_array, 5)  # 5% VaR
            conditional_value_at_risk = np.mean(returns_array[returns_array <= value_at_risk])
            
            # Risk-adjusted returns
            sharpe_ratio = mean_return / std_return if std_return > 0 else 0.0
            
            # Sortino ratio
            negative_returns = returns_array[returns_array < 0]
            if len(negative_returns) > 1:
                downside_std = np.std(negative_returns)
                sortino_ratio = mean_return / downside_std if downside_std > 0 else 0.0
            else:
                sortino_ratio = 0.0
            
            # Calmar ratio
            max_drawdowns = [result['max_drawdown'] for result in self.simulation_results]
            avg_max_drawdown = np.mean(max_drawdowns)
            calmar_ratio = mean_return / avg_max_drawdown if avg_max_drawdown > 0 else 0.0
            
            # Drawdown statistics
            max_drawdown_stats = {
                'mean': np.mean(max_drawdowns),
                'median': np.median(max_drawdowns),
                'std': np.std(max_drawdowns),
                'min': np.min(max_drawdowns),
                'max': np.max(max_drawdowns),
                'percentile_95': np.percentile(max_drawdowns, 95)
            }
            
            # Consecutive losses statistics
            consecutive_losses = [result['max_consecutive_losses'] for result in self.simulation_results]
            consecutive_losses_stats = {
                'mean': np.mean(consecutive_losses),
                'median': np.median(consecutive_losses),
                'std': np.std(consecutive_losses),
                'max': np.max(consecutive_losses),
                'percentile_95': np.percentile(consecutive_losses, 95)
            }
            
            # Consecutive wins statistics
            consecutive_wins = [result['max_consecutive_wins'] for result in self.simulation_results]
            consecutive_wins_stats = {
                'mean': np.mean(consecutive_wins),
                'median': np.median(consecutive_wins),
                'std': np.std(consecutive_wins),
                'max': np.max(consecutive_wins),
                'percentile_95': np.percentile(consecutive_wins, 95)
            }
            
            # Recovery time statistics (simplified)
            recovery_times = []
            for result in self.simulation_results:
                equity_curve = result['equity_curve']
                if len(equity_curve) > 1:
                    peak = equity_curve[0]
                    recovery_time = 0
                    for i, balance in enumerate(equity_curve[1:], 1):
                        if balance > peak:
                            recovery_time = i
                            peak = balance
                        else:
                            recovery_time += 1
                    recovery_times.append(recovery_time)
            
            recovery_time_stats = {
                'mean': np.mean(recovery_times) if recovery_times else 0,
                'median': np.median(recovery_times) if recovery_times else 0,
                'std': np.std(recovery_times) if recovery_times else 0,
                'max': np.max(recovery_times) if recovery_times else 0
            }
            
            return MonteCarloMetrics(
                mean_return=mean_return,
                median_return=median_return,
                std_return=std_return,
                min_return=min_return,
                max_return=max_return,
                skewness=skewness,
                kurtosis=kurtosis,
                percentiles=percentiles,
                confidence_intervals=confidence_intervals,
                probability_of_profit=probability_of_profit,
                probability_of_loss=probability_of_loss,
                probability_of_ruin=probability_of_ruin,
                expected_value=expected_value,
                value_at_risk=value_at_risk,
                conditional_value_at_risk=conditional_value_at_risk,
                sharpe_ratio=sharpe_ratio,
                sortino_ratio=sortino_ratio,
                calmar_ratio=calmar_ratio,
                max_drawdown_stats=max_drawdown_stats,
                consecutive_losses_stats=consecutive_losses_stats,
                consecutive_wins_stats=consecutive_wins_stats,
                recovery_time_stats=recovery_time_stats
            )
            
        except Exception as e:
            logger.error(f"❌ Error calculating Monte Carlo metrics: {e}")
            return None
    
    def generate_visualizations(self, save_path: str = None) -> List[str]:
        """Generate comprehensive visualizations"""
        try:
            if not self.simulation_results or not self.metrics:
                logger.error("❌ No simulation results available for visualization")
                return []
            
            # Set up plotting style
            plt.style.use('seaborn-v0_8')
            fig_paths = []
            
            # 1. Returns Distribution
            fig, ax = plt.subplots(figsize=(12, 8))
            returns = [result['total_return'] for result in self.simulation_results]
            
            ax.hist(returns, bins=50, alpha=0.7, color='skyblue', edgecolor='black')
            ax.axvline(self.metrics.mean_return, color='red', linestyle='--', 
                      label=f'Mean: {self.metrics.mean_return:.2f}%')
            ax.axvline(self.metrics.median_return, color='green', linestyle='--', 
                      label=f'Median: {self.metrics.median_return:.2f}%')
            ax.set_xlabel('Total Return (%)')
            ax.set_ylabel('Frequency')
            ax.set_title('Monte Carlo Simulation: Returns Distribution')
            ax.legend()
            ax.grid(True, alpha=0.3)
            
            if save_path:
                fig_path = os.path.join(save_path, 'returns_distribution.png')
                plt.savefig(fig_path, dpi=300, bbox_inches='tight')
                fig_paths.append(fig_path)
            plt.close()
            
            # 2. Drawdown Distribution
            fig, ax = plt.subplots(figsize=(12, 8))
            drawdowns = [result['max_drawdown'] for result in self.simulation_results]
            
            ax.hist(drawdowns, bins=50, alpha=0.7, color='lightcoral', edgecolor='black')
            ax.axvline(self.metrics.max_drawdown_stats['mean'], color='red', linestyle='--', 
                      label=f'Mean: {self.metrics.max_drawdown_stats["mean"]:.2f}%')
            ax.set_xlabel('Max Drawdown (%)')
            ax.set_ylabel('Frequency')
            ax.set_title('Monte Carlo Simulation: Drawdown Distribution')
            ax.legend()
            ax.grid(True, alpha=0.3)
            
            if save_path:
                fig_path = os.path.join(save_path, 'drawdown_distribution.png')
                plt.savefig(fig_path, dpi=300, bbox_inches='tight')
                fig_paths.append(fig_path)
            plt.close()
            
            # 3. Equity Curves Sample
            fig, ax = plt.subplots(figsize=(15, 8))
            
            # Plot sample of equity curves
            sample_size = min(100, len(self.simulation_results))
            sample_indices = np.random.choice(len(self.simulation_results), sample_size, replace=False)
            
            for idx in sample_indices:
                equity_curve = self.simulation_results[idx]['equity_curve']
                ax.plot(equity_curve, alpha=0.1, color='blue')
            
            # Plot mean equity curve
            if len(self.simulation_results) > 0:
                max_length = max(len(result['equity_curve']) for result in self.simulation_results)
                mean_curve = []
                for i in range(max_length):
                    values = []
                    for result in self.simulation_results:
                        if i < len(result['equity_curve']):
                            values.append(result['equity_curve'][i])
                    if values:
                        mean_curve.append(np.mean(values))
                
                ax.plot(mean_curve, color='red', linewidth=2, label='Mean Equity Curve')
            
            ax.set_xlabel('Trade Number')
            ax.set_ylabel('Account Balance')
            ax.set_title('Monte Carlo Simulation: Sample Equity Curves')
            ax.legend()
            ax.grid(True, alpha=0.3)
            
            if save_path:
                fig_path = os.path.join(save_path, 'equity_curves.png')
                plt.savefig(fig_path, dpi=300, bbox_inches='tight')
                fig_paths.append(fig_path)
            plt.close()
            
            # 4. Risk-Return Scatter
            fig, ax = plt.subplots(figsize=(12, 8))
            
            returns = [result['total_return'] for result in self.simulation_results]
            drawdowns = [result['max_drawdown'] for result in self.simulation_results]
            
            scatter = ax.scatter(drawdowns, returns, alpha=0.6, c=returns, cmap='RdYlGn')
            ax.set_xlabel('Max Drawdown (%)')
            ax.set_ylabel('Total Return (%)')
            ax.set_title('Monte Carlo Simulation: Risk vs Return')
            ax.grid(True, alpha=0.3)
            
            # Add colorbar
            cbar = plt.colorbar(scatter)
            cbar.set_label('Return (%)')
            
            if save_path:
                fig_path = os.path.join(save_path, 'risk_return_scatter.png')
                plt.savefig(fig_path, dpi=300, bbox_inches='tight')
                fig_paths.append(fig_path)
            plt.close()
            
            logger.info(f"📊 Generated {len(fig_paths)} visualizations")
            return fig_paths
            
        except Exception as e:
            logger.error(f"❌ Error generating visualizations: {e}")
            return []
    
    def generate_report(self) -> str:
        """Generate comprehensive Monte Carlo report"""
        if not self.metrics:
            return "No metrics available"
        
        report = []
        report.append("# ICT OTE Strategy Monte Carlo Simulation Report")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Simulations: {len(self.simulation_results)}")
        report.append("")
        
        # Return Statistics
        report.append("## Return Statistics")
        report.append(f"- **Mean Return:** {self.metrics.mean_return:.2f}%")
        report.append(f"- **Median Return:** {self.metrics.median_return:.2f}%")
        report.append(f"- **Standard Deviation:** {self.metrics.std_return:.2f}%")
        report.append(f"- **Min Return:** {self.metrics.min_return:.2f}%")
        report.append(f"- **Max Return:** {self.metrics.max_return:.2f}%")
        report.append(f"- **Skewness:** {self.metrics.skewness:.3f}")
        report.append(f"- **Kurtosis:** {self.metrics.kurtosis:.3f}")
        report.append("")
        
        # Percentiles
        report.append("## Return Percentiles")
        for level, value in self.metrics.percentiles.items():
            report.append(f"- **{level*100:.0f}th Percentile:** {value:.2f}%")
        report.append("")
        
        # Confidence Intervals
        report.append("## Confidence Intervals")
        for level, (lower, upper) in self.metrics.confidence_intervals.items():
            report.append(f"- **{level*100:.0f}% CI:** [{lower:.2f}%, {upper:.2f}%]")
        report.append("")
        
        # Probability Metrics
        report.append("## Probability Metrics")
        report.append(f"- **Probability of Profit:** {self.metrics.probability_of_profit:.1f}%")
        report.append(f"- **Probability of Loss:** {self.metrics.probability_of_loss:.1f}%")
        report.append(f"- **Probability of Ruin (50% loss):** {self.metrics.probability_of_ruin:.1f}%")
        report.append("")
        
        # Risk Metrics
        report.append("## Risk Metrics")
        report.append(f"- **Expected Value:** {self.metrics.expected_value:.2f}%")
        report.append(f"- **Value at Risk (5%):** {self.metrics.value_at_risk:.2f}%")
        report.append(f"- **Conditional VaR:** {self.metrics.conditional_value_at_risk:.2f}%")
        report.append("")
        
        # Risk-Adjusted Returns
        report.append("## Risk-Adjusted Returns")
        report.append(f"- **Sharpe Ratio:** {self.metrics.sharpe_ratio:.3f}")
        report.append(f"- **Sortino Ratio:** {self.metrics.sortino_ratio:.3f}")
        report.append(f"- **Calmar Ratio:** {self.metrics.calmar_ratio:.3f}")
        report.append("")
        
        # Drawdown Statistics
        report.append("## Drawdown Statistics")
        dd_stats = self.metrics.max_drawdown_stats
        report.append(f"- **Mean Max Drawdown:** {dd_stats['mean']:.2f}%")
        report.append(f"- **Median Max Drawdown:** {dd_stats['median']:.2f}%")
        report.append(f"- **95th Percentile Drawdown:** {dd_stats['percentile_95']:.2f}%")
        report.append(f"- **Worst Drawdown:** {dd_stats['max']:.2f}%")
        report.append("")
        
        # Consecutive Losses
        report.append("## Consecutive Losses Statistics")
        cl_stats = self.metrics.consecutive_losses_stats
        report.append(f"- **Mean Consecutive Losses:** {cl_stats['mean']:.1f}")
        report.append(f"- **Max Consecutive Losses:** {cl_stats['max']:.0f}")
        report.append(f"- **95th Percentile:** {cl_stats['percentile_95']:.1f}")
        report.append("")
        
        # Recommendations
        report.append("## Recommendations")
        
        if self.metrics.probability_of_profit > 60:
            report.append("✅ High probability of profit - strategy shows promise")
        else:
            report.append("⚠️ Low probability of profit - consider parameter optimization")
        
        if self.metrics.probability_of_ruin < 10:
            report.append("✅ Low probability of ruin - acceptable risk level")
        else:
            report.append("⚠️ High probability of ruin - consider reducing position size")
        
        if self.metrics.sharpe_ratio > 1.0:
            report.append("✅ Good Sharpe ratio - strategy is risk-adjusted profitable")
        else:
            report.append("⚠️ Low Sharpe ratio - consider improving risk-adjusted returns")
        
        if self.metrics.max_drawdown_stats['percentile_95'] < 30:
            report.append("✅ Acceptable drawdown risk - 95% of simulations under 30% drawdown")
        else:
            report.append("⚠️ High drawdown risk - consider reducing position size or improving strategy")
        
        return "\n".join(report)
    
    def save_results(self, filename: str = None) -> str:
        """Save Monte Carlo results to file"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"ict_ote_monte_carlo_{timestamp}.json"
        
        results = {
            'config': asdict(self.config),
            'metrics': asdict(self.metrics) if self.metrics else None,
            'simulation_results': self.simulation_results,
            'report': self.generate_report(),
            'timestamp': datetime.now().isoformat()
        }
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"💾 Results saved to {filename}")
        return filename

def main():
    """Main Monte Carlo simulation function"""
    # Configuration
    config = MonteCarloConfig(
        n_simulations=1000,
        confidence_levels=[0.05, 0.25, 0.5, 0.75, 0.95],
        bootstrap_samples=100,
        random_seed=42
    )
    
    # Test parameters
    test_parameters = {
        'ote_min_retracement': 0.50,
        'ote_max_retracement': 0.79,
        'fvg_min_size': 0.0005,
        'ob_lookback': 20,
        'stop_loss_atr': 2.0,
        'take_profit_atr': 4.0,
        'min_ote_strength': 70,
        'min_fvg_strength': 60
    }
    
    # Create Monte Carlo simulator
    monte_carlo = ICTOTEMonteCarlo(config)
    
    # Run simulation
    logger.info("🎲 Starting ICT OTE Strategy Monte Carlo Simulation...")
    metrics = monte_carlo.run_simulation(test_parameters)
    
    if metrics:
        # Generate and display report
        report = monte_carlo.generate_report()
        print("\n" + "="*80)
        print(report)
        print("="*80)
        
        # Generate visualizations
        try:
            os.makedirs('monte_carlo_plots', exist_ok=True)
            plot_paths = monte_carlo.generate_visualizations('monte_carlo_plots')
            print(f"\n📊 Visualizations saved to: monte_carlo_plots/")
        except Exception as e:
            logger.warning(f"⚠️ Could not generate visualizations: {e}")
        
        # Save results
        filename = monte_carlo.save_results()
        print(f"\n📊 Complete results saved to: {filename}")
        
    else:
        logger.error("❌ Monte Carlo simulation failed - no results generated")

if __name__ == "__main__":
    main()