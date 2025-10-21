#!/usr/bin/env python3
"""
Strategy Analyzer - Generates Actionable Insights
Analyzes strategy performance and provides recommendations
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class StrategyAnalyzer:
    """Analyze strategy performance and generate insights"""
    
    def __init__(self):
        """Initialize strategy analyzer"""
        self.thresholds = {
            'disable_loss': -1000,  # Disable if losing more than $1k
            'scale_up_profit': 5000,  # Scale up if profit > $5k
            'monitor_loss': -500,  # Monitor if losing $500-$1k
            'zero_trades_days': 2,  # Alert if 0 trades for 2 days
            'win_rate_low': 40,  # Low win rate threshold
            'win_rate_high': 70,  # High win rate threshold
        }
        logger.info("✅ Strategy analyzer initialized")
    
    def analyze_strategy(self, snapshot: Dict[str, Any], history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Analyze a single strategy and generate insights"""
        
        account_id = snapshot.get('account_id', '')
        display_name = snapshot.get('display_name', 'Unknown')
        pl = snapshot.get('pl', 0)
        unrealized_pl = snapshot.get('unrealized_pl', 0)
        trade_count = snapshot.get('trade_count', 0)
        win_rate = snapshot.get('win_rate', 0)
        
        # Determine status
        status = self._determine_status(pl, trade_count)
        
        # Generate recommendation
        recommendation = self._generate_recommendation(pl, unrealized_pl, trade_count, win_rate, history)
        
        # Calculate efficiency score (0-100)
        efficiency = self._calculate_efficiency(pl, win_rate, trade_count)
        
        # Determine trend
        trend = self._calculate_trend(history) if history else 'neutral'
        
        # Risk level
        risk_level = self._assess_risk(pl, unrealized_pl)
        
        return {
            'account_id': account_id,
            'display_name': display_name,
            'status': status,
            'recommendation': recommendation,
            'efficiency_score': efficiency,
            'trend': trend,
            'risk_level': risk_level,
            'action': recommendation['action'],
            'priority': recommendation['priority']
        }
    
    def _determine_status(self, pl: float, trade_count: int) -> str:
        """Determine strategy status"""
        if pl > self.thresholds['scale_up_profit']:
            return 'excellent'
        elif pl > 1000:
            return 'good'
        elif pl > -500:
            return 'neutral'
        elif pl > self.thresholds['disable_loss']:
            return 'warning'
        else:
            return 'critical'
    
    def _generate_recommendation(self, pl: float, unrealized_pl: float, 
                                 trade_count: int, win_rate: float,
                                 history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate actionable recommendation"""
        
        total_exposure = pl + unrealized_pl
        
        # Critical: Disable losing strategies
        if pl < self.thresholds['disable_loss']:
            return {
                'action': 'disable',
                'reason': f'Heavy losses (${pl:,.0f})',
                'detail': 'Strategy is losing significant capital. Consider disabling and analyzing root cause.',
                'priority': 'high',
                'icon': '🔴'
            }
        
        # Excellent: Scale up winners
        if pl > self.thresholds['scale_up_profit'] and win_rate > self.thresholds['win_rate_high']:
            return {
                'action': 'scale_up',
                'reason': f'Strong performer (+${pl:,.0f}, {win_rate:.1f}% WR)',
                'detail': 'Consistently profitable. Consider increasing position sizes by 50-100%.',
                'priority': 'high',
                'icon': '🟢'
            }
        
        # Monitor: Moderate losses
        if self.thresholds['monitor_loss'] < pl < 0:
            return {
                'action': 'monitor',
                'reason': f'Moderate losses (${pl:,.0f})',
                'detail': 'Watch closely. If losses continue, consider adjusting parameters or disabling.',
                'priority': 'medium',
                'icon': '🟡'
            }
        
        # Fix: No trades
        if trade_count == 0:
            return {
                'action': 'fix_criteria',
                'reason': 'Zero trades executed',
                'detail': 'Entry criteria may be too strict. Consider relaxing confidence threshold to 75-80%.',
                'priority': 'medium',
                'icon': '⚪'
            }
        
        # Fix: Low win rate
        if win_rate > 0 and win_rate < self.thresholds['win_rate_low']:
            return {
                'action': 'optimize',
                'reason': f'Low win rate ({win_rate:.1f}%)',
                'detail': 'Strategy needs optimization. Review entry/exit rules and risk management.',
                'priority': 'medium',
                'icon': '🟡'
            }
        
        # Good: Small profit
        if 0 < pl < 1000:
            return {
                'action': 'continue',
                'reason': f'Small profit (+${pl:,.0f})',
                'detail': 'Strategy showing promise. Monitor for consistency before scaling.',
                'priority': 'low',
                'icon': '🟢'
            }
        
        # Excellent but not scaled yet
        if pl > 1000:
            return {
                'action': 'monitor_for_scale',
                'reason': f'Good performance (+${pl:,.0f})',
                'detail': 'Performing well. Continue monitoring for scaling opportunity.',
                'priority': 'low',
                'icon': '🟢'
            }
        
        # Default: Keep running
        return {
            'action': 'continue',
            'reason': 'Break-even',
            'detail': 'Strategy is neutral. Continue monitoring performance.',
            'priority': 'low',
            'icon': '⚪'
        }
    
    def _calculate_efficiency(self, pl: float, win_rate: float, trade_count: int) -> int:
        """Calculate efficiency score (0-100)"""
        if trade_count == 0:
            return 0
        
        # Base score on P/L (40 points max)
        pl_score = min(40, max(0, (pl / 10000) * 40 + 20))
        
        # Win rate score (40 points max)
        wr_score = min(40, (win_rate / 100) * 40)
        
        # Activity score (20 points max)
        activity_score = min(20, (trade_count / 50) * 20)
        
        total_score = int(pl_score + wr_score + activity_score)
        return max(0, min(100, total_score))
    
    def _calculate_trend(self, history: List[Dict[str, Any]]) -> str:
        """Calculate performance trend from history"""
        if not history or len(history) < 2:
            return 'neutral'
        
        # Compare first half vs second half
        mid = len(history) // 2
        first_half_avg = sum(h['pl'] for h in history[:mid]) / mid
        second_half_avg = sum(h['pl'] for h in history[mid:]) / (len(history) - mid)
        
        change = second_half_avg - first_half_avg
        
        if change > 1000:
            return 'improving'
        elif change < -1000:
            return 'declining'
        else:
            return 'stable'
    
    def _assess_risk(self, pl: float, unrealized_pl: float) -> str:
        """Assess risk level"""
        total_exposure = abs(pl) + abs(unrealized_pl)
        
        if total_exposure > 5000:
            return 'high'
        elif total_exposure > 2000:
            return 'medium'
        else:
            return 'low'
    
    def generate_portfolio_insights(self, strategies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate insights for entire portfolio"""
        
        total_pl = sum(s.get('pl', 0) for s in strategies)
        avg_pl = total_pl / len(strategies) if strategies else 0
        
        winners = [s for s in strategies if s.get('pl', 0) > 500]
        losers = [s for s in strategies if s.get('pl', 0) < -500]
        neutral = [s for s in strategies if -500 <= s.get('pl', 0) <= 500]
        
        # Find best and worst
        best = max(strategies, key=lambda x: x.get('pl', 0)) if strategies else None
        worst = min(strategies, key=lambda x: x.get('pl', 0)) if strategies else None
        
        # Calculate total efficiency
        total_efficiency = sum(s.get('efficiency_score', 0) for s in strategies) / len(strategies) if strategies else 0
        
        # Generate recommendations
        recommendations = []
        
        if len(losers) > len(winners):
            recommendations.append({
                'type': 'warning',
                'message': f'{len(losers)} strategies losing (60%+). Consider disabling underperformers.',
                'priority': 'high'
            })
        
        if best and best.get('pl', 0) > 10000:
            recommendations.append({
                'type': 'success',
                'message': f"Scale up {best.get('display_name')} (+${best.get('pl', 0):,.0f})",
                'priority': 'high'
            })
        
        if total_efficiency < 50:
            recommendations.append({
                'type': 'warning',
                'message': 'Overall efficiency low. Review entry criteria and risk management.',
                'priority': 'medium'
            })
        
        return {
            'total_pl': total_pl,
            'avg_pl': avg_pl,
            'winners_count': len(winners),
            'losers_count': len(losers),
            'neutral_count': len(neutral),
            'best_performer': best,
            'worst_performer': worst,
            'total_efficiency': int(total_efficiency),
            'recommendations': recommendations
        }
    
    def get_actionable_list(self, strategies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get prioritized list of actionable items"""
        actions = []
        
        for strategy in strategies:
            analysis = self.analyze_strategy(strategy)
            
            if analysis['priority'] in ['high', 'medium']:
                actions.append({
                    'account_id': strategy.get('account_id'),
                    'display_name': strategy.get('display_name'),
                    'action': analysis['action'],
                    'reason': analysis['recommendation']['reason'],
                    'detail': analysis['recommendation']['detail'],
                    'priority': analysis['priority'],
                    'icon': analysis['recommendation']['icon']
                })
        
        # Sort by priority (high first)
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        actions.sort(key=lambda x: priority_order.get(x['priority'], 3))
        
        return actions


# Singleton instance
_strategy_analyzer = None

def get_strategy_analyzer() -> StrategyAnalyzer:
    """Get singleton strategy analyzer instance"""
    global _strategy_analyzer
    if _strategy_analyzer is None:
        _strategy_analyzer = StrategyAnalyzer()
    return _strategy_analyzer

