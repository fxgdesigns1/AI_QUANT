#!/usr/bin/env python3
"""
Example Integration Code - Roadmap Progress Tracking
Shows how to connect roadmap data with trade performance
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any
from src.analytics.trade_database import get_trade_database
from src.core.trump_dna_framework import get_trump_dna_planner


def calculate_roadmap_progress(week_start_date: str = None) -> Dict[str, Any]:
    """
    Calculate current progress against weekly roadmap
    
    Returns:
        {
            'week_info': {
                'current_day': 'Friday',
                'days_passed': 4,
                'days_remaining': 3
            },
            'targets': {
                'weekly_target': 15000.0,
                'current_progress': 8920.0,
                'expected_progress': 8571.0,
                'weekly_progress_pct': 59.5,
                'on_track': True
            },
            'daily_progress': [
                {
                    'day': 'Monday',
                    'target': 2500.0,
                    'actual': 2680.0,
                    'trades': 12,
                    'win_rate': 83.3,
                    'status': 'complete'
                },
                ...
            ],
            'strategy_progress': [
                {
                    'strategy_id': 'champion_75wr',
                    'pair': 'XAU_USD',
                    'target': 5000.0,
                    'current': 3240.0,
                    'progress_pct': 64.8,
                    'on_track': True
                },
                ...
            ]
        }
    """
    db = get_trade_database()
    
    # Get current week dates
    if week_start_date is None:
        today = datetime.now()
        # Get Monday of current week
        days_since_monday = today.weekday()
        week_start = today - timedelta(days=days_since_monday)
        week_end = week_start + timedelta(days=6)
    else:
        week_start = datetime.fromisoformat(week_start_date)
        week_end = week_start + timedelta(days=6)
    
    week_start_str = week_start.strftime('%Y-%m-%d')
    week_end_str = week_end.strftime('%Y-%m-%d')
    
    # Get roadmap data
    planner = get_trump_dna_planner()
    weekly_plans = planner.weekly_plans
    
    # Calculate overall progress
    total_weekly_target = sum(plan.weekly_target_dollars for plan in weekly_plans.values())
    
    # Get all trades for this week
    week_trades = db.get_trades_by_date_range(
        f"{week_start_str}T00:00:00",
        f"{week_end_str}T23:59:59"
    )
    
    # Filter closed trades only
    closed_trades = [t for t in week_trades if t.get('is_closed', 0) == 1]
    
    # Calculate current progress
    current_progress = sum(t.get('realized_pnl', 0) or 0 for t in closed_trades)
    
    # Calculate expected progress (linear based on days passed)
    days_passed = (datetime.now() - week_start).days + 1
    expected_progress = (total_weekly_target / 7) * days_passed
    
    # Calculate daily progress
    daily_progress = []
    for day_offset in range(7):
        day_date = week_start + timedelta(days=day_offset)
        day_name = day_date.strftime('%A')
        day_start = day_date.strftime('%Y-%m-%dT00:00:00')
        day_end = day_date.strftime('%Y-%m-%dT23:59:59')
        
        # Get trades for this day
        day_trades = db.get_trades_by_date_range(day_start, day_end)
        day_closed = [t for t in day_trades if t.get('is_closed', 0) == 1]
        
        # Calculate day metrics
        day_pnl = sum(t.get('realized_pnl', 0) or 0 for t in day_closed)
        day_wins = sum(1 for t in day_closed if (t.get('realized_pnl', 0) or 0) > 0)
        day_win_rate = (day_wins / len(day_closed) * 100) if day_closed else 0
        
        # Get target for this day (average daily target or from roadmap)
        daily_target = total_weekly_target / 7
        
        # Determine status
        if day_date.date() < datetime.now().date():
            status = 'complete'
        elif day_date.date() == datetime.now().date():
            status = 'current'
        else:
            status = 'upcoming'
        
        daily_progress.append({
            'day': day_name,
            'date': day_date.strftime('%Y-%m-%d'),
            'target': daily_target,
            'actual': day_pnl,
            'trades': len(day_closed),
            'wins': day_wins,
            'losses': len(day_closed) - day_wins,
            'win_rate': day_win_rate,
            'status': status
        })
    
    # Calculate strategy-specific progress
    strategy_progress = []
    for plan_key, plan in weekly_plans.items():
        strategy_id = plan.strategy_name.lower().replace(' ', '_')
        pair = plan.pair
        
        # Get trades for this strategy/pair this week
        strategy_trades = [
            t for t in closed_trades
            if t.get('strategy_id', '').lower() == strategy_id
            and t.get('instrument', '') == pair
        ]
        
        strategy_pnl = sum(t.get('realized_pnl', 0) or 0 for t in strategy_trades)
        strategy_target = plan.weekly_target_dollars
        strategy_progress_pct = (strategy_pnl / strategy_target * 100) if strategy_target > 0 else 0
        
        # Check if on track (should have made progress_pct of target by now)
        expected_strategy_progress = (strategy_target / 7) * days_passed
        on_track = strategy_pnl >= (expected_strategy_progress * 0.9)  # 90% tolerance
        
        strategy_progress.append({
            'strategy_id': strategy_id,
            'strategy_name': plan.strategy_name,
            'pair': pair,
            'target': strategy_target,
            'current': strategy_pnl,
            'progress_pct': strategy_progress_pct,
            'trades': len(strategy_trades),
            'on_track': on_track
        })
    
    # Overall on-track calculation
    weekly_progress_pct = (current_progress / total_weekly_target * 100) if total_weekly_target > 0 else 0
    on_track = current_progress >= (expected_progress * 0.9)  # 90% tolerance
    
    return {
        'week_info': {
            'week_start': week_start_str,
            'week_end': week_end_str,
            'current_day': datetime.now().strftime('%A'),
            'days_passed': days_passed,
            'days_remaining': 7 - days_passed,
            'week_progress_pct': (days_passed / 7) * 100
        },
        'targets': {
            'weekly_target': total_weekly_target,
            'current_progress': current_progress,
            'expected_progress': expected_progress,
            'weekly_progress_pct': weekly_progress_pct,
            'on_track': on_track,
            'variance': current_progress - expected_progress,
            'variance_pct': ((current_progress - expected_progress) / expected_progress * 100) if expected_progress > 0 else 0
        },
        'daily_progress': daily_progress,
        'strategy_progress': strategy_progress,
        'timestamp': datetime.now().isoformat()
    }


def get_filtered_performance(
    strategy_id: str = None,
    start_date: str = None,
    end_date: str = None,
    instrument: str = None,
    status: str = 'all'  # 'all', 'open', 'closed'
) -> Dict[str, Any]:
    """
    Get filtered performance data from trade database
    
    Returns:
        {
            'trades': [...],
            'metrics': {
                'total_trades': 42,
                'win_rate': 74.2,
                'total_pnl': 4520.30,
                ...
            },
            'strategies': [...]
        }
    """
    db = get_trade_database()
    
    # Build date range
    if start_date is None:
        start_date = (datetime.now() - timedelta(days=30)).isoformat()
    if end_date is None:
        end_date = datetime.now().isoformat()
    
    # Get trades with filters
    if strategy_id:
        # Get trades for specific strategy
        all_trades = db.get_trades_by_date_range(start_date, end_date, strategy_id)
    else:
        all_trades = db.get_trades_by_date_range(start_date, end_date)
    
    # Apply instrument filter
    if instrument:
        all_trades = [t for t in all_trades if t.get('instrument') == instrument]
    
    # Apply status filter
    if status == 'open':
        trades = [t for t in all_trades if t.get('is_closed', 0) == 0]
    elif status == 'closed':
        trades = [t for t in all_trades if t.get('is_closed', 0) == 1]
    else:
        trades = all_trades
    
    # Calculate metrics
    closed_trades = [t for t in trades if t.get('is_closed', 0) == 1]
    wins = sum(1 for t in closed_trades if (t.get('realized_pnl', 0) or 0) > 0)
    losses = len(closed_trades) - wins
    win_rate = (wins / len(closed_trades) * 100) if closed_trades else 0
    
    total_pnl = sum(t.get('realized_pnl', 0) or 0 for t in closed_trades)
    total_profit = sum(t.get('realized_pnl', 0) or 0 for t in closed_trades if (t.get('realized_pnl', 0) or 0) > 0)
    total_loss = abs(sum(t.get('realized_pnl', 0) or 0 for t in closed_trades if (t.get('realized_pnl', 0) or 0) < 0))
    
    profit_factor = (total_profit / total_loss) if total_loss > 0 else 0
    
    # Get strategy breakdown
    strategy_breakdown = {}
    for trade in closed_trades:
        sid = trade.get('strategy_id', 'unknown')
        if sid not in strategy_breakdown:
            strategy_breakdown[sid] = {
                'strategy_id': sid,
                'trades': 0,
                'wins': 0,
                'losses': 0,
                'pnl': 0
            }
        
        strategy_breakdown[sid]['trades'] += 1
        pnl = trade.get('realized_pnl', 0) or 0
        strategy_breakdown[sid]['pnl'] += pnl
        if pnl > 0:
            strategy_breakdown[sid]['wins'] += 1
        else:
            strategy_breakdown[sid]['losses'] += 1
    
    # Calculate win rates for each strategy
    for sid, data in strategy_breakdown.items():
        data['win_rate'] = (data['wins'] / data['trades'] * 100) if data['trades'] > 0 else 0
    
    return {
        'filters': {
            'strategy_id': strategy_id,
            'start_date': start_date,
            'end_date': end_date,
            'instrument': instrument,
            'status': status
        },
        'metrics': {
            'total_trades': len(trades),
            'open_trades': len([t for t in trades if t.get('is_closed', 0) == 0]),
            'closed_trades': len(closed_trades),
            'wins': wins,
            'losses': losses,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'total_profit': total_profit,
            'total_loss': total_loss,
            'profit_factor': profit_factor,
            'avg_win': (total_profit / wins) if wins > 0 else 0,
            'avg_loss': (total_loss / losses) if losses > 0 else 0
        },
        'strategies': list(strategy_breakdown.values()),
        'trades': trades[:100],  # Limit to 100 most recent
        'timestamp': datetime.now().isoformat()
    }


# Example Flask route integration
"""
@app.route('/api/roadmap/progress')
def api_roadmap_progress():
    try:
        week_start = request.args.get('week_start')
        progress = calculate_roadmap_progress(week_start)
        return jsonify({
            'success': True,
            'progress': progress
        })
    except Exception as e:
        logger.error(f"Error calculating roadmap progress: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/performance/filtered')
def api_performance_filtered():
    try:
        strategy_id = request.args.get('strategy_id')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        instrument = request.args.get('instrument')
        status = request.args.get('status', 'all')
        
        performance = get_filtered_performance(
            strategy_id=strategy_id,
            start_date=start_date,
            end_date=end_date,
            instrument=instrument,
            status=status
        )
        
        return jsonify({
            'success': True,
            'performance': performance
        })
    except Exception as e:
        logger.error(f"Error getting filtered performance: {e")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
"""
