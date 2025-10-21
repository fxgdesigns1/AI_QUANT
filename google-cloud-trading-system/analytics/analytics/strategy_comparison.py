#!/usr/bin/env python3
"""
Strategy Comparison Engine
A/B testing and statistical comparison of trading strategies
"""

import logging
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from scipy import stats

logger = logging.getLogger(__name__)


class StrategyComparison:
    """Statistical comparison of trading strategies"""
    
    def __init__(self, db):
        """Initialize with database connection"""
        self.db = db
        logger.info("✅ StrategyComparison initialized")
    
    def compare_strategies(self, 
                          strategy_a: str,
                          strategy_b: str,
                          days: int = 30,
                          confidence_level: float = 0.95) -> Dict:
        """
        Compare two strategies statistically
        
        Args:
            strategy_a: First strategy name
            strategy_b: Second strategy name
            days: Number of days to analyze
            confidence_level: Confidence level for statistical tests
        
        Returns:
            Comprehensive comparison results
        """
        try:
            # Get metrics for both strategies
            from .performance import PerformanceAnalytics
            analytics = PerformanceAnalytics(self.db)
            
            metrics_a = analytics.calculate_comprehensive_metrics(
                strategy_name=strategy_a,
                days=days
            )
            
            metrics_b = analytics.calculate_comprehensive_metrics(
                strategy_name=strategy_b,
                days=days
            )
            
            # Get daily returns for both
            returns_a = self.db.get_daily_returns(strategy_name=strategy_a, days=days)
            returns_b = self.db.get_daily_returns(strategy_name=strategy_b, days=days)
            
            # Statistical test (t-test for mean difference)
            if len(returns_a) > 1 and len(returns_b) > 1:
                t_stat, p_value = stats.ttest_ind(returns_a, returns_b)
                statistically_significant = p_value < (1 - confidence_level)
            else:
                t_stat, p_value = 0.0, 1.0
                statistically_significant = False
            
            # Calculate differences
            pl_diff = metrics_a['net_profit'] - metrics_b['net_profit']
            wr_diff = metrics_a['win_rate'] - metrics_b['win_rate']
            sharpe_diff = metrics_a['sharpe_ratio'] - metrics_b['sharpe_ratio']
            dd_diff = metrics_a['max_drawdown_pct'] - metrics_b['max_drawdown_pct']
            
            # Determine better strategy (multi-factor)
            score_a = self._calculate_strategy_score(metrics_a)
            score_b = self._calculate_strategy_score(metrics_b)
            
            better_strategy = strategy_a if score_a > score_b else strategy_b
            confidence_score = abs(score_a - score_b) / max(abs(score_a), abs(score_b), 1.0)
            
            # Generate recommendation
            recommendation = self._generate_recommendation(
                strategy_a, strategy_b,
                metrics_a, metrics_b,
                better_strategy, confidence_score,
                statistically_significant
            )
            
            comparison = {
                'strategy_a': strategy_a,
                'strategy_b': strategy_b,
                'period_days': days,
                
                # Metrics comparison
                'metrics_a': metrics_a,
                'metrics_b': metrics_b,
                
                # Differences
                'pl_difference': pl_diff,
                'win_rate_difference': wr_diff,
                'sharpe_difference': sharpe_diff,
                'drawdown_difference': dd_diff,
                
                # Statistical tests
                't_statistic': float(t_stat),
                'p_value': float(p_value),
                'confidence_level': confidence_level,
                'statistically_significant': statistically_significant,
                
                # Recommendation
                'better_strategy': better_strategy,
                'confidence_score': confidence_score,
                'strategy_a_score': score_a,
                'strategy_b_score': score_b,
                'recommendation': recommendation,
                
                'compared_at': datetime.now().isoformat()
            }
            
            # Store comparison
            self.db.conn.execute("""
                INSERT INTO strategy_comparisons (
                    comparison_id, timestamp, strategy_a, strategy_b, time_period,
                    pl_difference, win_rate_difference, sharpe_difference, drawdown_difference,
                    t_statistic, p_value, confidence_level, statistically_significant,
                    better_strategy, confidence_score, recommendation
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f"{strategy_a}_vs_{strategy_b}_{datetime.now().timestamp()}",
                datetime.now().isoformat(),
                strategy_a, strategy_b, f"{days}d",
                pl_diff, wr_diff, sharpe_diff, dd_diff,
                t_stat, p_value, confidence_level, statistically_significant,
                better_strategy, confidence_score, recommendation
            ))
            self.db.conn.commit()
            
            logger.info(f"✅ Compared {strategy_a} vs {strategy_b}")
            return comparison
            
        except Exception as e:
            logger.error(f"❌ Strategy comparison failed: {e}")
            return {}
    
    def _calculate_strategy_score(self, metrics: Dict) -> float:
        """
        Calculate composite strategy score
        Weighs multiple factors
        """
        # Weighted scoring
        score = (
            metrics.get('sharpe_ratio', 0.0) * 0.3 +      # 30% Sharpe
            metrics.get('profit_factor', 0.0) * 0.2 +     # 20% Profit Factor
            metrics.get('win_rate', 0.0) / 100 * 0.15 +   # 15% Win Rate
            (1 - metrics.get('max_drawdown_pct', 1.0)) * 0.20 +  # 20% Low Drawdown
            metrics.get('sortino_ratio', 0.0) * 0.15      # 15% Sortino
        )
        
        return score
    
    def _generate_recommendation(self, 
                                 strategy_a: str, 
                                 strategy_b: str,
                                 metrics_a: Dict,
                                 metrics_b: Dict,
                                 better_strategy: str,
                                 confidence_score: float,
                                 significant: bool) -> str:
        """Generate human-readable recommendation"""
        
        if confidence_score > 0.3 and significant:
            return f"Strong recommendation: Use {better_strategy}. Statistically significant outperformance."
        elif confidence_score > 0.15:
            return f"Moderate recommendation: {better_strategy} shows better performance, but continue monitoring."
        else:
            return f"Inconclusive: Both strategies show similar performance. Need more data or longer testing period."


