#!/usr/bin/env python3
"""
Change Impact Analyzer
Analyze the impact of strategy parameter changes on performance
"""

import logging
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ChangeImpactAnalyzer:
    """Analyze impact of strategy changes"""
    
    def __init__(self, db):
        """Initialize with database connection"""
        self.db = db
        logger.info("✅ ChangeImpactAnalyzer initialized")
    
    def analyze_change_impact(self, 
                             change_id: str,
                             lookback_days: int = 30) -> Dict:
        """
        Analyze the impact of a specific strategy change
        
        Args:
            change_id: ID of the change to analyze
            lookback_days: Days before/after to compare
        
        Returns:
            Impact analysis results
        """
        try:
            # Get change details
            cursor = self.db.conn.cursor()
            cursor.execute("""
                SELECT * FROM strategy_changes WHERE change_id = ?
            """, (change_id,))
            
            change = cursor.fetchone()
            if not change:
                logger.error(f"Change {change_id} not found")
                return {}
            
            change_dict = dict(change)
            change_time = datetime.fromisoformat(change_dict['timestamp'])
            strategy_name = change_dict['strategy_name']
            account_id = change_dict['account_id']
            
            # Get trades before change
            before_start = change_time - timedelta(days=lookback_days)
            trades_before = self.db.get_trades(
                strategy_name=strategy_name,
                account_id=account_id,
                start_date=before_start,
                end_date=change_time,
                status='closed'
            )
            
            # Get trades after change
            after_end = change_time + timedelta(days=lookback_days)
            trades_after = self.db.get_trades(
                strategy_name=strategy_name,
                account_id=account_id,
                start_date=change_time,
                end_date=after_end,
                status='closed'
            )
            
            # Calculate metrics
            from .performance import PerformanceAnalytics
            analytics = PerformanceAnalytics(self.db)
            
            before_metrics = self._calculate_metrics_from_trades(trades_before, analytics)
            after_metrics = self._calculate_metrics_from_trades(trades_after, analytics)
            
            # Calculate improvements
            improvement = {
                'win_rate': after_metrics['win_rate'] - before_metrics['win_rate'],
                'avg_pl': after_metrics['avg_trade_pl'] - before_metrics['avg_trade_pl'],
                'sharpe': after_metrics['sharpe_ratio'] - before_metrics['sharpe_ratio'],
                'profit_factor': after_metrics['profit_factor'] - before_metrics['profit_factor'],
                'max_drawdown': before_metrics['max_drawdown_pct'] - after_metrics['max_drawdown_pct']  # Negative is good
            }
            
            # Calculate improvement score (-4 to +4)
            improvement_score = sum([
                1 if improvement['win_rate'] > 0 else -1,
                1 if improvement['avg_pl'] > 0 else -1,
                1 if improvement['sharpe'] > 0 else -1,
                1 if improvement['profit_factor'] > 0 else -1
            ])
            
            # Generate recommendation
            if improvement_score >= 3:
                recommendation = "Keep - Significant improvement"
            elif improvement_score >= 1:
                recommendation = "Keep - Moderate improvement"
            elif improvement_score == 0:
                recommendation = "Monitor - Neutral impact"
            elif improvement_score >= -2:
                recommendation = "Consider reverting - Slight decline"
            else:
                recommendation = "Revert - Significant decline"
            
            # Update change record with results
            cursor.execute("""
                UPDATE strategy_changes
                SET trades_after = ?,
                    win_rate_after = ?,
                    avg_pl_after = ?,
                    sharpe_after = ?,
                    impact_analyzed = TRUE,
                    impact_score = ?,
                    recommendation = ?
                WHERE change_id = ?
            """, (
                len(trades_after),
                after_metrics['win_rate'],
                after_metrics['avg_trade_pl'],
                after_metrics['sharpe_ratio'],
                improvement_score,
                recommendation,
                change_id
            ))
            self.db.conn.commit()
            
            analysis = {
                'change_id': change_id,
                'parameter_changed': change_dict['parameter_changed'],
                'old_value': change_dict['old_value'],
                'new_value': change_dict['new_value'],
                'change_time': change_time.isoformat(),
                'lookback_days': lookback_days,
                
                'before_metrics': before_metrics,
                'after_metrics': after_metrics,
                'improvement': improvement,
                'improvement_score': improvement_score,
                
                'recommendation': recommendation,
                'confidence': abs(improvement_score) / 4.0,  # 0 to 1
                
                'analyzed_at': datetime.now().isoformat()
            }
            
            logger.info(f"✅ Analyzed change {change_id}: {recommendation}")
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Change impact analysis failed: {e}")
            return {}
    
    def _calculate_metrics_from_trades(self, trades: List[Dict], analytics) -> Dict:
        """Calculate metrics from trade list"""
        if not trades:
            return {
                'total_trades': 0,
                'win_rate': 0.0,
                'avg_trade_pl': 0.0,
                'sharpe_ratio': 0.0,
                'profit_factor': 0.0,
                'max_drawdown_pct': 0.0
            }
        
        winning = [t for t in trades if t.get('net_pl', 0) > 0]
        losing = [t for t in trades if t.get('net_pl', 0) < 0]
        
        gross_profit = sum(t['net_pl'] for t in winning)
        gross_loss = abs(sum(t['net_pl'] for t in losing))
        
        returns = [t.get('net_pl', 0) for t in trades]
        
        return {
            'total_trades': len(trades),
            'win_rate': (len(winning) / len(trades) * 100) if trades else 0.0,
            'avg_trade_pl': np.mean(returns) if returns else 0.0,
            'sharpe_ratio': analytics.calculate_sharpe_ratio(returns) if returns else 0.0,
            'profit_factor': (gross_profit / gross_loss) if gross_loss > 0 else 0.0,
            'max_drawdown_pct': 0.0  # Would need equity curve
        }


