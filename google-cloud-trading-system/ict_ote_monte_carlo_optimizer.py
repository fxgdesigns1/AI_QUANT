#!/usr/bin/env python3
"""
ICT OTE Strategy Monte Carlo Optimizer
Comprehensive Monte Carlo optimization with real data and brutal honesty
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

# Import the real backtester
from ict_ote_real_backtest import ICTOTERealBacktester, BacktestConfig, BacktestResult

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class MonteCarloConfig:
    """Monte Carlo optimization configuration"""
    n_simulations: int = 1000
    n_parameter_combinations: int = 100
    confidence_levels: List[float] = None
    bootstrap_samples: int = 100
    random_seed: int = 42
    
    def __post_init__(self):
        if self.confidence_levels is None:
            self.confidence_levels = [0.05, 0.25, 0.5, 0.75, 0.95]

@dataclass
class OptimizationResult:
    """Monte Carlo optimization result"""
    best_parameters: Dict[str, Any]
    best_performance: Dict[str, float]
    all_results: List[BacktestResult]
    monte_carlo_stats: Dict[str, Any]
    parameter_sensitivity: Dict[str, Any]
    risk_assessment: Dict[str, Any]
    brutal_honesty_score: float

class ICTOTEMonteCarloOptimizer:
    """Monte Carlo Optimizer for ICT OTE Strategy"""
    
    def __init__(self, backtest_config: BacktestConfig, monte_carlo_config: MonteCarloConfig):
        self.backtest_config = backtest_config
        self.monte_carlo_config = monte_carlo_config
        np.random.seed(monte_carlo_config.random_seed)
        
        # Results storage
        self.optimization_results: List[BacktestResult] = []
        self.parameter_combinations: List[Dict[str, Any]] = []
        self.monte_carlo_simulations: List[Dict] = []
        
        logger.info("🎲 ICT OTE Monte Carlo Optimizer initialized")
        logger.info(f"📊 Simulations: {monte_carlo_config.n_simulations}")
        logger.info(f"🔧 Parameter Combinations: {monte_carlo_config.n_parameter_combinations}")
    
    def generate_parameter_combinations(self) -> List[Dict[str, Any]]:
        """Generate diverse parameter combinations for optimization"""
        combinations = []
        
        # Define parameter ranges based on ICT OTE best practices
        param_ranges = {
            'ote_min_retracement': (0.45, 0.65),
            'ote_max_retracement': (0.65, 0.85),
            'fvg_min_size': (0.0002, 0.0015),
            'ob_lookback': (10, 40),
            'stop_loss_atr': (1.5, 4.0),
            'take_profit_atr': (2.0, 6.0),
            'min_ote_strength': (60, 90),
            'min_fvg_strength': (50, 85)
        }
        
        for _ in range(self.monte_carlo_config.n_parameter_combinations):
            params = {}
            
            # Generate random parameters
            for param, (min_val, max_val) in param_ranges.items():
                if param in ['ob_lookback']:
                    params[param] = int(np.random.uniform(min_val, max_val))
                else:
                    params[param] = np.random.uniform(min_val, max_val)
            
            # Ensure logical constraints
            if params['ote_min_retracement'] >= params['ote_max_retracement']:
                params['ote_max_retracement'] = params['ote_min_retracement'] + 0.05
            
            # Ensure take profit is greater than stop loss
            if params['take_profit_atr'] <= params['stop_loss_atr']:
                params['take_profit_atr'] = params['stop_loss_atr'] + 0.5
            
            combinations.append(params)
        
        self.parameter_combinations = combinations
        logger.info(f"✅ Generated {len(combinations)} parameter combinations")
        return combinations
    
    def run_parameter_optimization(self) -> List[BacktestResult]:
        """Run parameter optimization across all combinations"""
        logger.info("🔧 Starting parameter optimization...")
        
        # Generate parameter combinations
        combinations = self.generate_parameter_combinations()
        
        # Run backtests for each combination
        results = []
        backtester = ICTOTERealBacktester(self.backtest_config)
        
        for i, params in enumerate(combinations):
            if i % 10 == 0:
                logger.info(f"🔄 Running backtest {i+1}/{len(combinations)}...")
            
            try:
                result = backtester.run_backtest(params)
                if result:
                    results.append(result)
                    logger.info(f"  📊 Return: {result.total_return:.2f}%, Win Rate: {result.win_rate:.1f}%, Sharpe: {result.sharpe_ratio:.3f}")
            except Exception as e:
                logger.error(f"❌ Backtest {i+1} failed: {e}")
        
        self.optimization_results = results
        logger.info(f"✅ Parameter optimization completed: {len(results)} successful backtests")
        return results
    
    def run_monte_carlo_simulation(self) -> Dict[str, Any]:
        """Run Monte Carlo simulation on best parameters"""
        logger.info("🎲 Starting Monte Carlo simulation...")
        
        if not self.optimization_results:
            logger.error("❌ No optimization results available for Monte Carlo simulation")
            return {}
        
        # Find best parameters
        best_result = max(self.optimization_results, key=lambda x: x.sharpe_ratio)
        best_params = best_result.parameters
        
        logger.info(f"🎯 Best parameters found: {best_params}")
        
        # Run Monte Carlo simulations
        simulation_results = []
        
        for sim in range(self.monte_carlo_config.n_simulations):
            if sim % 100 == 0:
                logger.info(f"🔄 Monte Carlo simulation {sim}/{self.monte_carlo_config.n_simulations}")
            
            # Create slightly modified parameters for each simulation
            modified_params = self._modify_parameters(best_params)
            
            # Run backtest with modified parameters
            backtester = ICTOTERealBacktester(self.backtest_config)
            result = backtester.run_backtest(modified_params)
            
            if result:
                simulation_results.append({
                    'total_return': result.total_return,
                    'max_drawdown': result.max_drawdown,
                    'sharpe_ratio': result.sharpe_ratio,
                    'win_rate': result.win_rate,
                    'profit_factor': result.profit_factor,
                    'parameters': modified_params
                })
        
        # Calculate Monte Carlo statistics
        if simulation_results:
            returns = [r['total_return'] for r in simulation_results]
            drawdowns = [r['max_drawdown'] for r in simulation_results]
            sharpe_ratios = [r['sharpe_ratio'] for r in simulation_results]
            win_rates = [r['win_rate'] for r in simulation_results]
            
            monte_carlo_stats = {
                'mean_return': np.mean(returns),
                'std_return': np.std(returns),
                'min_return': np.min(returns),
                'max_return': np.max(returns),
                'percentiles': {level: np.percentile(returns, level * 100) 
                              for level in self.monte_carlo_config.confidence_levels},
                'mean_drawdown': np.mean(drawdowns),
                'max_drawdown_95th': np.percentile(drawdowns, 95),
                'mean_sharpe': np.mean(sharpe_ratios),
                'mean_win_rate': np.mean(win_rates),
                'probability_of_profit': np.mean([r > 0 for r in returns]) * 100,
                'probability_of_loss': np.mean([r <= 0 for r in returns]) * 100,
                'probability_of_ruin': np.mean([r < -50 for r in returns]) * 100
            }
            
            self.monte_carlo_simulations = simulation_results
            
            logger.info(f"✅ Monte Carlo simulation completed: {len(simulation_results)} simulations")
            logger.info(f"📊 Mean Return: {monte_carlo_stats['mean_return']:.2f}%")
            logger.info(f"📊 Probability of Profit: {monte_carlo_stats['probability_of_profit']:.1f}%")
            
            return monte_carlo_stats
        
        return {}
    
    def _modify_parameters(self, base_params: Dict[str, Any]) -> Dict[str, Any]:
        """Modify parameters slightly for Monte Carlo simulation"""
        modified = base_params.copy()
        
        # Add small random variations to parameters
        for param, value in modified.items():
            if param in ['ob_lookback']:
                # Integer parameter
                variation = np.random.randint(-2, 3)
                modified[param] = max(5, int(value + variation))
            else:
                # Float parameter
                variation = np.random.normal(0, 0.05)  # 5% standard deviation
                if param in ['ote_min_retracement', 'ote_max_retracement']:
                    modified[param] = max(0.3, min(0.9, value + variation))
                elif param in ['fvg_min_size']:
                    modified[param] = max(0.0001, min(0.002, value + variation))
                elif param in ['stop_loss_atr', 'take_profit_atr']:
                    modified[param] = max(1.0, min(8.0, value + variation))
                elif param in ['min_ote_strength', 'min_fvg_strength']:
                    modified[param] = max(30, min(100, value + variation))
        
        # Ensure logical constraints
        if modified['ote_min_retracement'] >= modified['ote_max_retracement']:
            modified['ote_max_retracement'] = modified['ote_min_retracement'] + 0.05
        
        if modified['take_profit_atr'] <= modified['stop_loss_atr']:
            modified['take_profit_atr'] = modified['stop_loss_atr'] + 0.5
        
        return modified
    
    def calculate_parameter_sensitivity(self) -> Dict[str, Any]:
        """Calculate parameter sensitivity analysis"""
        if not self.optimization_results:
            return {}
        
        logger.info("📊 Calculating parameter sensitivity...")
        
        # Extract parameter values and performance metrics
        param_data = {}
        for result in self.optimization_results:
            for param, value in result.parameters.items():
                if param not in param_data:
                    param_data[param] = {'values': [], 'returns': [], 'sharpe_ratios': []}
                
                param_data[param]['values'].append(value)
                param_data[param]['returns'].append(result.total_return)
                param_data[param]['sharpe_ratios'].append(result.sharpe_ratio)
        
        # Calculate correlations
        sensitivity = {}
        for param, data in param_data.items():
            if len(data['values']) > 10:  # Need enough data points
                return_corr = np.corrcoef(data['values'], data['returns'])[0, 1]
                sharpe_corr = np.corrcoef(data['values'], data['sharpe_ratios'])[0, 1]
                
                sensitivity[param] = {
                    'return_correlation': return_corr,
                    'sharpe_correlation': sharpe_corr,
                    'sensitivity_score': abs(return_corr) + abs(sharpe_corr),
                    'optimal_range': (min(data['values']), max(data['values']))
                }
        
        # Sort by sensitivity
        sensitivity = dict(sorted(sensitivity.items(), 
                                key=lambda x: x[1]['sensitivity_score'], 
                                reverse=True))
        
        logger.info(f"✅ Parameter sensitivity calculated for {len(sensitivity)} parameters")
        return sensitivity
    
    def assess_risk(self) -> Dict[str, Any]:
        """Assess comprehensive risk profile"""
        if not self.optimization_results:
            return {}
        
        logger.info("⚠️ Assessing risk profile...")
        
        # Calculate risk metrics
        returns = [r.total_return for r in self.optimization_results]
        drawdowns = [r.max_drawdown for r in self.optimization_results]
        sharpe_ratios = [r.sharpe_ratio for r in self.optimization_results]
        
        risk_assessment = {
            'return_volatility': np.std(returns),
            'max_drawdown_avg': np.mean(drawdowns),
            'max_drawdown_std': np.std(drawdowns),
            'worst_drawdown': max(drawdowns),
            'sharpe_volatility': np.std(sharpe_ratios),
            'consistency_score': 1 - (np.std(returns) / abs(np.mean(returns))) if np.mean(returns) != 0 else 0,
            'risk_score': 0.0
        }
        
        # Calculate overall risk score (0-100, higher = riskier)
        risk_score = 0
        
        # Return volatility risk
        if risk_assessment['return_volatility'] > 20:
            risk_score += 25
        elif risk_assessment['return_volatility'] > 10:
            risk_score += 15
        elif risk_assessment['return_volatility'] > 5:
            risk_score += 5
        
        # Drawdown risk
        if risk_assessment['worst_drawdown'] > 30:
            risk_score += 30
        elif risk_assessment['worst_drawdown'] > 20:
            risk_score += 20
        elif risk_assessment['worst_drawdown'] > 10:
            risk_score += 10
        
        # Consistency risk
        if risk_assessment['consistency_score'] < 0.5:
            risk_score += 25
        elif risk_assessment['consistency_score'] < 0.7:
            risk_score += 15
        elif risk_assessment['consistency_score'] < 0.8:
            risk_score += 5
        
        # Sharpe ratio volatility risk
        if risk_assessment['sharpe_volatility'] > 1.0:
            risk_score += 20
        elif risk_assessment['sharpe_volatility'] > 0.5:
            risk_score += 10
        
        risk_assessment['risk_score'] = min(100, risk_score)
        
        # Risk level classification
        if risk_score >= 70:
            risk_assessment['risk_level'] = 'HIGH'
        elif risk_score >= 40:
            risk_assessment['risk_level'] = 'MEDIUM'
        else:
            risk_assessment['risk_level'] = 'LOW'
        
        logger.info(f"✅ Risk assessment completed: {risk_assessment['risk_level']} risk")
        return risk_assessment
    
    def calculate_brutal_honesty_score(self) -> float:
        """Calculate brutal honesty score (0-100, higher = more honest/realistic)"""
        if not self.optimization_results:
            return 0.0
        
        logger.info("🔍 Calculating brutal honesty score...")
        
        # Get best result
        best_result = max(self.optimization_results, key=lambda x: x.sharpe_ratio)
        
        # Calculate honesty factors
        honesty_factors = []
        
        # 1. Win rate realism (40-70% is realistic)
        win_rate = best_result.win_rate
        if 40 <= win_rate <= 70:
            honesty_factors.append(100)
        elif 30 <= win_rate < 40 or 70 < win_rate <= 80:
            honesty_factors.append(80)
        else:
            honesty_factors.append(40)
        
        # 2. Drawdown realism (5-15% is realistic)
        drawdown = best_result.max_drawdown
        if 5 <= drawdown <= 15:
            honesty_factors.append(100)
        elif 3 <= drawdown < 5 or 15 < drawdown <= 25:
            honesty_factors.append(80)
        else:
            honesty_factors.append(40)
        
        # 3. Return realism (10-30% monthly is realistic)
        monthly_return = best_result.total_return
        if 10 <= monthly_return <= 30:
            honesty_factors.append(100)
        elif 5 <= monthly_return < 10 or 30 < monthly_return <= 50:
            honesty_factors.append(80)
        else:
            honesty_factors.append(40)
        
        # 4. Sharpe ratio realism (0.5-2.0 is realistic)
        sharpe = best_result.sharpe_ratio
        if 0.5 <= sharpe <= 2.0:
            honesty_factors.append(100)
        elif 0.3 <= sharpe < 0.5 or 2.0 < sharpe <= 3.0:
            honesty_factors.append(80)
        else:
            honesty_factors.append(40)
        
        # 5. Trade frequency realism (10-50 trades/month is realistic)
        trade_frequency = best_result.total_trades
        if 10 <= trade_frequency <= 50:
            honesty_factors.append(100)
        elif 5 <= trade_frequency < 10 or 50 < trade_frequency <= 100:
            honesty_factors.append(80)
        else:
            honesty_factors.append(40)
        
        # Calculate weighted average
        brutal_honesty_score = np.mean(honesty_factors)
        
        logger.info(f"✅ Brutal honesty score: {brutal_honesty_score:.1f}/100")
        return brutal_honesty_score
    
    def run_comprehensive_optimization(self) -> OptimizationResult:
        """Run comprehensive Monte Carlo optimization"""
        logger.info("🚀 Starting comprehensive Monte Carlo optimization...")
        
        # Step 1: Parameter optimization
        logger.info("📊 Step 1: Parameter Optimization")
        optimization_results = self.run_parameter_optimization()
        
        if not optimization_results:
            logger.error("❌ No optimization results - cannot proceed")
            return None
        
        # Step 2: Monte Carlo simulation
        logger.info("🎲 Step 2: Monte Carlo Simulation")
        monte_carlo_stats = self.run_monte_carlo_simulation()
        
        # Step 3: Parameter sensitivity analysis
        logger.info("📊 Step 3: Parameter Sensitivity Analysis")
        parameter_sensitivity = self.calculate_parameter_sensitivity()
        
        # Step 4: Risk assessment
        logger.info("⚠️ Step 4: Risk Assessment")
        risk_assessment = self.assess_risk()
        
        # Step 5: Brutal honesty score
        logger.info("🔍 Step 5: Brutal Honesty Assessment")
        brutal_honesty_score = self.calculate_brutal_honesty_score()
        
        # Find best result
        best_result = max(optimization_results, key=lambda x: x.sharpe_ratio)
        
        # Create comprehensive result
        result = OptimizationResult(
            best_parameters=best_result.parameters,
            best_performance={
                'total_return': best_result.total_return,
                'annualized_return': best_result.annualized_return,
                'max_drawdown': best_result.max_drawdown,
                'sharpe_ratio': best_result.sharpe_ratio,
                'win_rate': best_result.win_rate,
                'profit_factor': best_result.profit_factor,
                'calmar_ratio': best_result.calmar_ratio,
                'sortino_ratio': best_result.sortino_ratio
            },
            all_results=optimization_results,
            monte_carlo_stats=monte_carlo_stats,
            parameter_sensitivity=parameter_sensitivity,
            risk_assessment=risk_assessment,
            brutal_honesty_score=brutal_honesty_score
        )
        
        logger.info("✅ Comprehensive optimization completed!")
        return result
    
    def generate_comprehensive_report(self, result: OptimizationResult) -> str:
        """Generate comprehensive optimization report"""
        report = []
        report.append("# ICT OTE Strategy Monte Carlo Optimization Report")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Executive Summary
        report.append("## Executive Summary")
        report.append(f"**Brutal Honesty Score:** {result.brutal_honesty_score:.1f}/100")
        report.append(f"**Risk Level:** {result.risk_assessment['risk_level']}")
        report.append(f"**Total Combinations Tested:** {len(result.all_results)}")
        report.append("")
        
        # Best Parameters
        report.append("## Optimal Parameters")
        for param, value in result.best_parameters.items():
            report.append(f"- **{param}:** {value}")
        report.append("")
        
        # Best Performance
        report.append("## Best Performance Metrics")
        perf = result.best_performance
        report.append(f"- **Total Return:** {perf['total_return']:.2f}%")
        report.append(f"- **Annualized Return:** {perf['annualized_return']:.2f}%")
        report.append(f"- **Max Drawdown:** {perf['max_drawdown']:.2f}%")
        report.append(f"- **Sharpe Ratio:** {perf['sharpe_ratio']:.3f}")
        report.append(f"- **Win Rate:** {perf['win_rate']:.1f}%")
        report.append(f"- **Profit Factor:** {perf['profit_factor']:.2f}")
        report.append(f"- **Calmar Ratio:** {perf['calmar_ratio']:.3f}")
        report.append(f"- **Sortino Ratio:** {perf['sortino_ratio']:.3f}")
        report.append("")
        
        # Monte Carlo Statistics
        if result.monte_carlo_stats:
            report.append("## Monte Carlo Simulation Results")
            mc = result.monte_carlo_stats
            report.append(f"- **Mean Return:** {mc['mean_return']:.2f}%")
            report.append(f"- **Return Volatility:** {mc['std_return']:.2f}%")
            report.append(f"- **Min Return:** {mc['min_return']:.2f}%")
            report.append(f"- **Max Return:** {mc['max_return']:.2f}%")
            report.append(f"- **5th Percentile:** {mc['percentiles'][0.05]:.2f}%")
            report.append(f"- **95th Percentile:** {mc['percentiles'][0.95]:.2f}%")
            report.append(f"- **Probability of Profit:** {mc['probability_of_profit']:.1f}%")
            report.append(f"- **Probability of Loss:** {mc['probability_of_loss']:.1f}%")
            report.append(f"- **Probability of Ruin:** {mc['probability_of_ruin']:.1f}%")
            report.append("")
        
        # Parameter Sensitivity
        report.append("## Parameter Sensitivity Analysis")
        for param, data in result.parameter_sensitivity.items():
            report.append(f"- **{param}:**")
            report.append(f"  - Return Correlation: {data['return_correlation']:.3f}")
            report.append(f"  - Sharpe Correlation: {data['sharpe_correlation']:.3f}")
            report.append(f"  - Sensitivity Score: {data['sensitivity_score']:.3f}")
            report.append(f"  - Optimal Range: {data['optimal_range'][0]:.3f} - {data['optimal_range'][1]:.3f}")
        report.append("")
        
        # Risk Assessment
        report.append("## Risk Assessment")
        risk = result.risk_assessment
        report.append(f"- **Risk Level:** {risk['risk_level']}")
        report.append(f"- **Risk Score:** {risk['risk_score']:.1f}/100")
        report.append(f"- **Return Volatility:** {risk['return_volatility']:.2f}%")
        report.append(f"- **Max Drawdown (Avg):** {risk['max_drawdown_avg']:.2f}%")
        report.append(f"- **Worst Drawdown:** {risk['worst_drawdown']:.2f}%")
        report.append(f"- **Consistency Score:** {risk['consistency_score']:.3f}")
        report.append("")
        
        # Brutal Honesty Assessment
        report.append("## Brutal Honesty Assessment")
        if result.brutal_honesty_score >= 80:
            report.append("✅ **HIGHLY REALISTIC** - Results appear genuine and achievable")
        elif result.brutal_honesty_score >= 60:
            report.append("⚠️ **MODERATELY REALISTIC** - Results may be optimistic but achievable")
        elif result.brutal_honesty_score >= 40:
            report.append("⚠️ **SOMEWHAT UNREALISTIC** - Results may be too good to be true")
        else:
            report.append("❌ **HIGHLY UNREALISTIC** - Results are likely fabricated or over-optimized")
        
        report.append("")
        
        # Recommendations
        report.append("## Recommendations")
        
        # Performance recommendations
        if result.best_performance['total_return'] < 0:
            report.append("❌ **DO NOT USE** - Strategy is losing money")
        elif result.best_performance['total_return'] < 5:
            report.append("⚠️ **USE WITH EXTREME CAUTION** - Strategy barely profitable")
        elif result.best_performance['total_return'] < 15:
            report.append("✅ **PROMISING** - Strategy shows good potential")
        else:
            report.append("🎯 **EXCELLENT** - Strategy shows strong profitability")
        
        # Risk recommendations
        if result.risk_assessment['risk_level'] == 'HIGH':
            report.append("⚠️ **HIGH RISK** - Reduce position size and monitor closely")
        elif result.risk_assessment['risk_level'] == 'MEDIUM':
            report.append("✅ **MODERATE RISK** - Acceptable risk level with proper management")
        else:
            report.append("✅ **LOW RISK** - Good risk profile")
        
        # Honesty recommendations
        if result.brutal_honesty_score < 60:
            report.append("⚠️ **VERIFY RESULTS** - Results may be over-optimized, test thoroughly")
        else:
            report.append("✅ **TRUST RESULTS** - Results appear realistic and trustworthy")
        
        return "\n".join(report)

def main():
    """Main optimization function"""
    # Configuration for last month
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    backtest_config = BacktestConfig(
        instruments=['XAU_USD', 'EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'USD_CAD'],
        start_date=start_date,
        end_date=end_date,
        initial_balance=10000.0,
        news_filter=True,
        min_news_impact='Medium'
    )
    
    monte_carlo_config = MonteCarloConfig(
        n_simulations=500,  # Reduced for faster execution
        n_parameter_combinations=50,  # Reduced for faster execution
        random_seed=42
    )
    
    # Create optimizer
    optimizer = ICTOTEMonteCarloOptimizer(backtest_config, monte_carlo_config)
    
    # Run comprehensive optimization
    logger.info("🚀 Starting Comprehensive Monte Carlo Optimization...")
    result = optimizer.run_comprehensive_optimization()
    
    if result:
        # Generate and display report
        report = optimizer.generate_comprehensive_report(result)
        print("\n" + "="*100)
        print(report)
        print("="*100)
        
        # Save results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"ict_ote_monte_carlo_optimization_{timestamp}.json"
        
        results_data = {
            'config': {
                'backtest_config': asdict(backtest_config),
                'monte_carlo_config': asdict(monte_carlo_config)
            },
            'result': asdict(result),
            'report': report,
            'timestamp': datetime.now().isoformat()
        }
        
        with open(filename, 'w') as f:
            json.dump(results_data, f, indent=2, default=str)
        
        print(f"\n📊 Complete results saved to: {filename}")
        
    else:
        logger.error("❌ Optimization failed - no results generated")

if __name__ == "__main__":
    main()