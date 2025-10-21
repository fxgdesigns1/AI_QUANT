#!/usr/bin/env python3
"""
ICT OTE Strategy Comprehensive Optimizer
Complete optimization system with backtesting, Monte Carlo simulation, and parameter optimization
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

from ict_ote_optimizer import ICTOTEOptimizer, OptimizationConfig
from ict_ote_backtester import ICTOTEBacktester, BacktestConfig
from ict_ote_monte_carlo import ICTOTEMonteCarlo, MonteCarloConfig

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ComprehensiveConfig:
    """Comprehensive optimization configuration"""
    instruments: List[str]
    start_date: datetime
    end_date: datetime
    initial_balance: float = 10000.0
    
    # Optimization parameters
    n_optimization_combinations: int = 50
    optimization_metrics: List[str] = None
    
    # Backtesting parameters
    backtest_granularity: str = 'M15'
    commission_rate: float = 0.0001
    spread_pips: float = 1.5
    max_trades_per_day: int = 20
    max_positions: int = 3
    risk_per_trade: float = 0.02
    
    # Monte Carlo parameters
    n_monte_carlo_simulations: int = 1000
    monte_carlo_confidence_levels: List[float] = None
    
    def __post_init__(self):
        if self.optimization_metrics is None:
            self.optimization_metrics = ['sharpe_ratio', 'total_return', 'max_drawdown']
        if self.monte_carlo_confidence_levels is None:
            self.monte_carlo_confidence_levels = [0.05, 0.25, 0.5, 0.75, 0.95]

@dataclass
class ComprehensiveResults:
    """Comprehensive optimization results"""
    optimization_results: Dict[str, Any]
    backtest_results: Dict[str, Any]
    monte_carlo_results: Dict[str, Any]
    best_parameters: Dict[str, Any]
    performance_summary: Dict[str, Any]
    recommendations: List[str]
    risk_assessment: Dict[str, Any]
    final_score: float

class ICTOTEComprehensiveOptimizer:
    """Comprehensive ICT OTE Strategy Optimizer"""
    
    def __init__(self, config: ComprehensiveConfig):
        self.config = config
        
        # Initialize components
        self.optimizer = ICTOTEOptimizer(OptimizationConfig(
            instruments=config.instruments,
            start_date=config.start_date,
            end_date=config.end_date,
            initial_balance=config.initial_balance
        ))
        
        self.backtester = ICTOTEBacktester(BacktestConfig(
            instruments=config.instruments,
            start_date=config.start_date,
            end_date=config.end_date,
            initial_balance=config.initial_balance,
            granularity=config.backtest_granularity,
            commission_rate=config.commission_rate,
            spread_pips=config.spread_pips,
            max_trades_per_day=config.max_trades_per_day,
            max_positions=config.max_positions,
            risk_per_trade=config.risk_per_trade
        ))
        
        self.monte_carlo = ICTOTEMonteCarlo(MonteCarloConfig(
            n_simulations=config.n_monte_carlo_simulations,
            confidence_levels=config.monte_carlo_confidence_levels
        ))
        
        # Results storage
        self.results: Optional[ComprehensiveResults] = None
        
        logger.info("🚀 ICT OTE Comprehensive Optimizer initialized")
        logger.info(f"📊 Instruments: {config.instruments}")
        logger.info(f"📅 Period: {config.start_date.strftime('%Y-%m-%d')} to {config.end_date.strftime('%Y-%m-%d')}")
    
    def run_comprehensive_optimization(self) -> ComprehensiveResults:
        """Run comprehensive optimization process"""
        try:
            logger.info("🚀 Starting comprehensive ICT OTE optimization...")
            
            # Step 1: Parameter Optimization
            logger.info("🔧 Step 1: Parameter Optimization")
            optimization_results = self.optimizer.run_optimization(
                n_combinations=self.config.n_optimization_combinations
            )
            
            if not optimization_results:
                logger.error("❌ Parameter optimization failed")
                return None
            
            best_parameters = optimization_results['best_parameters']
            logger.info(f"✅ Best parameters found: {best_parameters}")
            
            # Step 2: Detailed Backtesting
            logger.info("📊 Step 2: Detailed Backtesting")
            backtest_metrics = self.backtester.run_backtest(best_parameters)
            
            if not backtest_metrics:
                logger.error("❌ Backtesting failed")
                return None
            
            logger.info(f"✅ Backtesting completed: {backtest_metrics.total_return:.2f}% return")
            
            # Step 3: Monte Carlo Simulation
            logger.info("🎲 Step 3: Monte Carlo Simulation")
            monte_carlo_metrics = self.monte_carlo.run_simulation(best_parameters)
            
            if not monte_carlo_metrics:
                logger.error("❌ Monte Carlo simulation failed")
                return None
            
            logger.info(f"✅ Monte Carlo completed: {monte_carlo_metrics.probability_of_profit:.1f}% profit probability")
            
            # Step 4: Comprehensive Analysis
            logger.info("📈 Step 4: Comprehensive Analysis")
            performance_summary = self._calculate_performance_summary(
                optimization_results, backtest_metrics, monte_carlo_metrics
            )
            
            recommendations = self._generate_recommendations(
                optimization_results, backtest_metrics, monte_carlo_metrics
            )
            
            risk_assessment = self._assess_risk(monte_carlo_metrics)
            
            final_score = self._calculate_final_score(
                optimization_results, backtest_metrics, monte_carlo_metrics
            )
            
            # Create comprehensive results
            self.results = ComprehensiveResults(
                optimization_results=optimization_results,
                backtest_results=asdict(backtest_metrics),
                monte_carlo_results=asdict(monte_carlo_metrics),
                best_parameters=best_parameters,
                performance_summary=performance_summary,
                recommendations=recommendations,
                risk_assessment=risk_assessment,
                final_score=final_score
            )
            
            logger.info(f"✅ Comprehensive optimization completed! Final Score: {final_score:.2f}")
            
            return self.results
            
        except Exception as e:
            logger.error(f"❌ Comprehensive optimization failed: {e}")
            return None
    
    def _calculate_performance_summary(self, optimization_results: Dict, 
                                     backtest_metrics, monte_carlo_metrics) -> Dict[str, Any]:
        """Calculate comprehensive performance summary"""
        try:
            # Extract key metrics
            opt_perf = optimization_results['best_performance']
            
            summary = {
                'total_return': {
                    'optimization': opt_perf['total_return'],
                    'backtest': backtest_metrics.total_return,
                    'monte_carlo_mean': monte_carlo_metrics.mean_return
                },
                'risk_metrics': {
                    'max_drawdown': {
                        'optimization': opt_perf['max_drawdown'],
                        'backtest': backtest_metrics.max_drawdown,
                        'monte_carlo_mean': monte_carlo_metrics.max_drawdown_stats['mean']
                    },
                    'sharpe_ratio': {
                        'optimization': opt_perf['sharpe_ratio'],
                        'backtest': backtest_metrics.sharpe_ratio,
                        'monte_carlo': monte_carlo_metrics.sharpe_ratio
                    }
                },
                'consistency_metrics': {
                    'win_rate': backtest_metrics.win_rate,
                    'profit_factor': backtest_metrics.profit_factor,
                    'probability_of_profit': monte_carlo_metrics.probability_of_profit,
                    'probability_of_ruin': monte_carlo_metrics.probability_of_ruin
                },
                'risk_adjusted_returns': {
                    'sortino_ratio': backtest_metrics.sortino_ratio,
                    'calmar_ratio': backtest_metrics.calmar_ratio,
                    'recovery_factor': backtest_metrics.recovery_factor
                }
            }
            
            # Calculate consistency score
            consistency_score = self._calculate_consistency_score(summary)
            summary['consistency_score'] = consistency_score
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ Error calculating performance summary: {e}")
            return {}
    
    def _calculate_consistency_score(self, summary: Dict) -> float:
        """Calculate consistency score across different methods"""
        try:
            scores = []
            
            # Return consistency
            returns = [
                summary['total_return']['optimization'],
                summary['total_return']['backtest'],
                summary['total_return']['monte_carlo_mean']
            ]
            return_std = np.std(returns)
            return_mean = np.mean(returns)
            return_consistency = max(0, 1 - (return_std / abs(return_mean))) if return_mean != 0 else 0
            scores.append(return_consistency)
            
            # Drawdown consistency
            drawdowns = [
                summary['risk_metrics']['max_drawdown']['optimization'],
                summary['risk_metrics']['max_drawdown']['backtest'],
                summary['risk_metrics']['max_drawdown']['monte_carlo_mean']
            ]
            drawdown_std = np.std(drawdowns)
            drawdown_mean = np.mean(drawdowns)
            drawdown_consistency = max(0, 1 - (drawdown_std / drawdown_mean)) if drawdown_mean != 0 else 0
            scores.append(drawdown_consistency)
            
            # Sharpe ratio consistency
            sharpe_ratios = [
                summary['risk_metrics']['sharpe_ratio']['optimization'],
                summary['risk_metrics']['sharpe_ratio']['backtest'],
                summary['risk_metrics']['sharpe_ratio']['monte_carlo']
            ]
            sharpe_std = np.std(sharpe_ratios)
            sharpe_mean = np.mean(sharpe_ratios)
            sharpe_consistency = max(0, 1 - (sharpe_std / abs(sharpe_mean))) if sharpe_mean != 0 else 0
            scores.append(sharpe_consistency)
            
            return np.mean(scores) * 100
            
        except Exception as e:
            logger.error(f"❌ Error calculating consistency score: {e}")
            return 0.0
    
    def _generate_recommendations(self, optimization_results: Dict, 
                                backtest_metrics, monte_carlo_metrics) -> List[str]:
        """Generate comprehensive recommendations"""
        recommendations = []
        
        try:
            # Performance recommendations
            if backtest_metrics.total_return > 20:
                recommendations.append("✅ Excellent return potential - strategy shows strong profitability")
            elif backtest_metrics.total_return > 10:
                recommendations.append("✅ Good return potential - strategy is profitable")
            elif backtest_metrics.total_return > 0:
                recommendations.append("⚠️ Modest returns - consider parameter optimization")
            else:
                recommendations.append("❌ Negative returns - strategy needs significant improvement")
            
            # Risk recommendations
            if backtest_metrics.max_drawdown < 10:
                recommendations.append("✅ Low drawdown risk - excellent risk management")
            elif backtest_metrics.max_drawdown < 20:
                recommendations.append("✅ Acceptable drawdown risk - good risk management")
            elif backtest_metrics.max_drawdown < 30:
                recommendations.append("⚠️ Moderate drawdown risk - consider reducing position size")
            else:
                recommendations.append("❌ High drawdown risk - reduce position size or improve strategy")
            
            # Consistency recommendations
            if backtest_metrics.win_rate > 60:
                recommendations.append("✅ High win rate - strategy is consistent")
            elif backtest_metrics.win_rate > 50:
                recommendations.append("✅ Good win rate - strategy is reasonably consistent")
            else:
                recommendations.append("⚠️ Low win rate - consider improving entry criteria")
            
            # Monte Carlo recommendations
            if monte_carlo_metrics.probability_of_profit > 70:
                recommendations.append("✅ High probability of profit in Monte Carlo simulation")
            elif monte_carlo_metrics.probability_of_profit > 60:
                recommendations.append("✅ Good probability of profit in Monte Carlo simulation")
            else:
                recommendations.append("⚠️ Low probability of profit - strategy may be risky")
            
            if monte_carlo_metrics.probability_of_ruin < 5:
                recommendations.append("✅ Very low probability of ruin - excellent risk control")
            elif monte_carlo_metrics.probability_of_ruin < 15:
                recommendations.append("✅ Low probability of ruin - good risk control")
            else:
                recommendations.append("⚠️ Moderate probability of ruin - consider reducing risk")
            
            # Sharpe ratio recommendations
            if backtest_metrics.sharpe_ratio > 2.0:
                recommendations.append("✅ Excellent Sharpe ratio - outstanding risk-adjusted returns")
            elif backtest_metrics.sharpe_ratio > 1.5:
                recommendations.append("✅ Very good Sharpe ratio - strong risk-adjusted returns")
            elif backtest_metrics.sharpe_ratio > 1.0:
                recommendations.append("✅ Good Sharpe ratio - positive risk-adjusted returns")
            else:
                recommendations.append("⚠️ Low Sharpe ratio - consider improving risk-adjusted returns")
            
            # Profit factor recommendations
            if backtest_metrics.profit_factor > 2.0:
                recommendations.append("✅ Excellent profit factor - strong profitability")
            elif backtest_metrics.profit_factor > 1.5:
                recommendations.append("✅ Good profit factor - profitable strategy")
            elif backtest_metrics.profit_factor > 1.0:
                recommendations.append("⚠️ Modest profit factor - strategy is barely profitable")
            else:
                recommendations.append("❌ Poor profit factor - strategy is unprofitable")
            
            # Kelly percentage recommendations
            if 0 < backtest_metrics.kelly_percentage < 10:
                recommendations.append("✅ Optimal Kelly percentage - good position sizing")
            elif backtest_metrics.kelly_percentage > 20:
                recommendations.append("⚠️ High Kelly percentage - consider reducing position size")
            else:
                recommendations.append("ℹ️ Kelly percentage suggests conservative position sizing")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"❌ Error generating recommendations: {e}")
            return ["❌ Error generating recommendations"]
    
    def _assess_risk(self, monte_carlo_metrics) -> Dict[str, Any]:
        """Assess comprehensive risk profile"""
        try:
            risk_assessment = {
                'overall_risk_level': 'medium',
                'risk_factors': [],
                'risk_score': 0.0,
                'risk_mitigation': []
            }
            
            risk_score = 0.0
            risk_factors = []
            risk_mitigation = []
            
            # Probability of ruin assessment
            if monte_carlo_metrics.probability_of_ruin > 20:
                risk_score += 30
                risk_factors.append("High probability of ruin (>20%)")
                risk_mitigation.append("Reduce position size significantly")
            elif monte_carlo_metrics.probability_of_ruin > 10:
                risk_score += 20
                risk_factors.append("Moderate probability of ruin (10-20%)")
                risk_mitigation.append("Consider reducing position size")
            elif monte_carlo_metrics.probability_of_ruin > 5:
                risk_score += 10
                risk_factors.append("Low probability of ruin (5-10%)")
            else:
                risk_factors.append("Very low probability of ruin (<5%)")
            
            # Drawdown risk assessment
            if monte_carlo_metrics.max_drawdown_stats['percentile_95'] > 40:
                risk_score += 25
                risk_factors.append("High drawdown risk (95th percentile >40%)")
                risk_mitigation.append("Implement stricter stop losses")
            elif monte_carlo_metrics.max_drawdown_stats['percentile_95'] > 25:
                risk_score += 15
                risk_factors.append("Moderate drawdown risk (95th percentile 25-40%)")
                risk_mitigation.append("Consider reducing position size")
            elif monte_carlo_metrics.max_drawdown_stats['percentile_95'] > 15:
                risk_score += 5
                risk_factors.append("Low drawdown risk (95th percentile 15-25%)")
            else:
                risk_factors.append("Very low drawdown risk (95th percentile <15%)")
            
            # Consecutive losses assessment
            if monte_carlo_metrics.consecutive_losses_stats['percentile_95'] > 10:
                risk_score += 20
                risk_factors.append("High consecutive loss risk (95th percentile >10)")
                risk_mitigation.append("Implement maximum consecutive loss limits")
            elif monte_carlo_metrics.consecutive_losses_stats['percentile_95'] > 5:
                risk_score += 10
                risk_factors.append("Moderate consecutive loss risk (95th percentile 5-10)")
            else:
                risk_factors.append("Low consecutive loss risk (95th percentile <5)")
            
            # Volatility assessment
            if monte_carlo_metrics.std_return > 30:
                risk_score += 15
                risk_factors.append("High return volatility (>30%)")
                risk_mitigation.append("Consider smoothing entry signals")
            elif monte_carlo_metrics.std_return > 20:
                risk_score += 10
                risk_factors.append("Moderate return volatility (20-30%)")
            else:
                risk_factors.append("Low return volatility (<20%)")
            
            # Determine overall risk level
            if risk_score >= 70:
                risk_assessment['overall_risk_level'] = 'high'
            elif risk_score >= 40:
                risk_assessment['overall_risk_level'] = 'medium'
            else:
                risk_assessment['overall_risk_level'] = 'low'
            
            risk_assessment['risk_score'] = risk_score
            risk_assessment['risk_factors'] = risk_factors
            risk_assessment['risk_mitigation'] = risk_mitigation
            
            return risk_assessment
            
        except Exception as e:
            logger.error(f"❌ Error assessing risk: {e}")
            return {'overall_risk_level': 'unknown', 'risk_factors': [], 'risk_score': 0.0, 'risk_mitigation': []}
    
    def _calculate_final_score(self, optimization_results: Dict, 
                             backtest_metrics, monte_carlo_metrics) -> float:
        """Calculate final comprehensive score"""
        try:
            scores = []
            
            # Return score (0-25 points)
            return_score = min(25, max(0, backtest_metrics.total_return * 1.25))
            scores.append(return_score)
            
            # Risk score (0-25 points)
            risk_score = max(0, 25 - backtest_metrics.max_drawdown)
            scores.append(risk_score)
            
            # Consistency score (0-20 points)
            consistency_score = min(20, backtest_metrics.win_rate * 0.2)
            scores.append(consistency_score)
            
            # Sharpe ratio score (0-15 points)
            sharpe_score = min(15, max(0, backtest_metrics.sharpe_ratio * 7.5))
            scores.append(sharpe_score)
            
            # Monte Carlo score (0-15 points)
            mc_score = min(15, monte_carlo_metrics.probability_of_profit * 0.15)
            scores.append(mc_score)
            
            final_score = sum(scores)
            
            logger.info(f"📊 Final Score Breakdown:")
            logger.info(f"   Return Score: {return_score:.1f}/25")
            logger.info(f"   Risk Score: {risk_score:.1f}/25")
            logger.info(f"   Consistency Score: {consistency_score:.1f}/20")
            logger.info(f"   Sharpe Score: {sharpe_score:.1f}/15")
            logger.info(f"   Monte Carlo Score: {mc_score:.1f}/15")
            logger.info(f"   Total Score: {final_score:.1f}/100")
            
            return final_score
            
        except Exception as e:
            logger.error(f"❌ Error calculating final score: {e}")
            return 0.0
    
    def generate_comprehensive_report(self) -> str:
        """Generate comprehensive optimization report"""
        if not self.results:
            return "No results available"
        
        report = []
        report.append("# ICT OTE Strategy Comprehensive Optimization Report")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Executive Summary
        report.append("## Executive Summary")
        report.append(f"**Final Score:** {self.results.final_score:.1f}/100")
        report.append(f"**Overall Risk Level:** {self.results.risk_assessment['overall_risk_level'].upper()}")
        report.append(f"**Best Parameters Found:** {len(self.results.best_parameters)} parameters optimized")
        report.append("")
        
        # Best Parameters
        report.append("## Optimized Parameters")
        for param, value in self.results.best_parameters.items():
            report.append(f"- **{param}:** {value}")
        report.append("")
        
        # Performance Summary
        report.append("## Performance Summary")
        perf = self.results.performance_summary
        
        report.append("### Returns")
        report.append(f"- **Optimization Return:** {perf['total_return']['optimization']:.2f}%")
        report.append(f"- **Backtest Return:** {perf['total_return']['backtest']:.2f}%")
        report.append(f"- **Monte Carlo Mean:** {perf['total_return']['monte_carlo_mean']:.2f}%")
        report.append("")
        
        report.append("### Risk Metrics")
        report.append(f"- **Max Drawdown (Backtest):** {perf['risk_metrics']['max_drawdown']['backtest']:.2f}%")
        report.append(f"- **Sharpe Ratio (Backtest):** {perf['risk_metrics']['sharpe_ratio']['backtest']:.3f}")
        report.append(f"- **Sortino Ratio:** {perf['risk_adjusted_returns']['sortino_ratio']:.3f}")
        report.append(f"- **Calmar Ratio:** {perf['risk_adjusted_returns']['calmar_ratio']:.3f}")
        report.append("")
        
        report.append("### Consistency Metrics")
        report.append(f"- **Win Rate:** {perf['consistency_metrics']['win_rate']:.1f}%")
        report.append(f"- **Profit Factor:** {perf['consistency_metrics']['profit_factor']:.2f}")
        report.append(f"- **Probability of Profit:** {perf['consistency_metrics']['probability_of_profit']:.1f}%")
        report.append(f"- **Probability of Ruin:** {perf['consistency_metrics']['probability_of_ruin']:.1f}%")
        report.append("")
        
        # Risk Assessment
        report.append("## Risk Assessment")
        risk = self.results.risk_assessment
        report.append(f"**Overall Risk Level:** {risk['overall_risk_level'].upper()}")
        report.append(f"**Risk Score:** {risk['risk_score']:.1f}/100")
        report.append("")
        
        if risk['risk_factors']:
            report.append("### Risk Factors")
            for factor in risk['risk_factors']:
                report.append(f"- {factor}")
            report.append("")
        
        if risk['risk_mitigation']:
            report.append("### Risk Mitigation Recommendations")
            for mitigation in risk['risk_mitigation']:
                report.append(f"- {mitigation}")
            report.append("")
        
        # Recommendations
        report.append("## Recommendations")
        for i, rec in enumerate(self.results.recommendations, 1):
            report.append(f"{i}. {rec}")
        report.append("")
        
        # Next Steps
        report.append("## Next Steps")
        report.append("1. **Paper Trading:** Test optimized parameters in paper trading for 1-2 weeks")
        report.append("2. **Live Monitoring:** Monitor performance closely during initial live trading")
        report.append("3. **Parameter Adjustment:** Fine-tune parameters based on live performance")
        report.append("4. **Risk Management:** Implement recommended risk mitigation measures")
        report.append("5. **Performance Review:** Conduct weekly performance reviews")
        report.append("")
        
        # Implementation Notes
        report.append("## Implementation Notes")
        report.append("- Start with smaller position sizes to validate strategy")
        report.append("- Monitor drawdown closely and adjust position size if needed")
        report.append("- Consider implementing maximum consecutive loss limits")
        report.append("- Regularly review and update parameters based on market conditions")
        report.append("- Keep detailed trade logs for further analysis")
        
        return "\n".join(report)
    
    def save_comprehensive_results(self, filename: str = None) -> str:
        """Save comprehensive results to file"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"ict_ote_comprehensive_optimization_{timestamp}.json"
        
        results = {
            'config': asdict(self.config),
            'results': asdict(self.results) if self.results else None,
            'report': self.generate_comprehensive_report(),
            'timestamp': datetime.now().isoformat()
        }
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"💾 Comprehensive results saved to {filename}")
        return filename

def main():
    """Main comprehensive optimization function"""
    # Configuration
    config = ComprehensiveConfig(
        instruments=['XAU_USD', 'EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'USD_CAD'],
        start_date=datetime.now() - timedelta(days=60),  # Last 60 days
        end_date=datetime.now(),
        initial_balance=10000.0,
        n_optimization_combinations=30,
        n_monte_carlo_simulations=500
    )
    
    # Create comprehensive optimizer
    optimizer = ICTOTEComprehensiveOptimizer(config)
    
    # Run comprehensive optimization
    logger.info("🚀 Starting Comprehensive ICT OTE Strategy Optimization...")
    results = optimizer.run_comprehensive_optimization()
    
    if results:
        # Generate and display report
        report = optimizer.generate_comprehensive_report()
        print("\n" + "="*100)
        print(report)
        print("="*100)
        
        # Save results
        filename = optimizer.save_comprehensive_results()
        print(f"\n📊 Complete results saved to: {filename}")
        
        # Generate visualizations if possible
        try:
            os.makedirs('comprehensive_plots', exist_ok=True)
            plot_paths = optimizer.monte_carlo.generate_visualizations('comprehensive_plots')
            print(f"\n📊 Visualizations saved to: comprehensive_plots/")
        except Exception as e:
            logger.warning(f"⚠️ Could not generate visualizations: {e}")
        
    else:
        logger.error("❌ Comprehensive optimization failed - no results generated")

if __name__ == "__main__":
    main()