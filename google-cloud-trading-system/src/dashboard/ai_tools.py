from typing import Dict, Any, List, Tuple
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

class PolicyViolation(Exception):
    pass


def summarize_market(data_feed, accounts: List[str]) -> Dict[str, Any]:
    summary = {}
    for account_id in accounts:
        try:
            market = data_feed.get_market_data(account_id)
            if not market:
                continue
            for instrument, md in market.items():
                key = f"{account_id}:{instrument}"
                summary[key] = {
                    'bid': md.bid,
                    'ask': md.ask,
                    'spread': md.spread,
                    'timestamp': md.timestamp,
                    'is_live': md.is_live,
                    'volatility_score': getattr(md, 'volatility_score', None),
                    'last_update_age': getattr(md, 'last_update_age', None),
                    'regime': getattr(md, 'regime', None)
                }
        except Exception:
            continue
    return summary


def get_positions_preview(order_manager, account_id: str) -> List[Dict[str, Any]]:
    positions: List[Dict[str, Any]] = []
    try:
        trades = order_manager.get_trades(account_id)
        for t in trades or []:
            if getattr(t, 'status', None) == 'OPEN':
                positions.append({
                    'instrument': t.instrument,
                    'side': getattr(t.side, 'value', t.side),
                    'units': t.units,
                    'entry_price': t.entry_price,
                    'unrealized_pl': t.unrealized_pl
                })
    except Exception:
        pass
    return positions


def compute_portfolio_exposure(account_manager, order_manager, accounts: List[str]) -> Tuple[float, int]:
    total_balance = 0.0
    total_margin_used = 0.0
    total_positions = 0
    for account_id in accounts:
        try:
            status = account_manager.get_account_status(account_id) or {}
            total_balance += float(status.get('balance', 0.0))
            daily = order_manager.get_daily_stats(account_id) or {}
            total_margin_used += float(daily.get('margin_used', 0.0))
            total_positions += int(daily.get('open_positions', 0))
        except Exception:
            continue
    exposure = (total_margin_used / total_balance) if total_balance else 0.0
    return exposure, total_positions


def enforce_policy(account_manager, order_manager, accounts: List[str], max_exposure: float = 0.10, max_positions: int = 5) -> None:
    exposure, positions = compute_portfolio_exposure(account_manager, order_manager, accounts)
    if exposure > max_exposure:
        raise PolicyViolation(f"Portfolio exposure {exposure:.3f} exceeds cap {max_exposure:.3f}")
    if positions > max_positions:
        raise PolicyViolation(f"Open positions {positions} exceed cap {max_positions}")


def preview_close_positions(order_manager, account_id: str, instrument: str, side: str = 'buy') -> Dict[str, Any]:
    matched: List[Dict[str, Any]] = []
    try:
        trades = order_manager.get_trades(account_id)
        for t in trades or []:
            if getattr(t, 'status', None) == 'OPEN' and t.instrument.replace('_', '').lower() in [instrument.replace('_', '').lower()] and getattr(t.side, 'value', t.side).lower() == side.lower():
                matched.append({
                    'trade_id': getattr(t, 'id', None),
                    'instrument': t.instrument,
                    'side': getattr(t.side, 'value', t.side),
                    'units': t.units,
                    'entry_price': t.entry_price
                })
    except Exception:
        pass
    return {
        'instrument': instrument,
        'side': side,
        'positions_matched': len(matched),
        'orders_preview': matched
    }


def get_full_market_context(data_feed, accounts: List[str], shadow_system=None) -> Dict[str, Any]:
    """Get comprehensive market context for AI analysis"""
    try:
        context = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'market_data': summarize_market(data_feed, accounts),
            'trading_session': _get_current_trading_session(),
            'volatility_analysis': _analyze_volatility(data_feed, accounts),
            'news_sentiment': _get_news_sentiment(),
            'economic_events': _get_upcoming_events()
        }
        
        if shadow_system:
            context.update({
                'system_health': shadow_system.get_system_health(),
                'recent_signals': shadow_system.get_shadow_signals(limit=5),
                'strategy_performance': shadow_system.get_strategy_performance()
            })
        
        return context
    except Exception as e:
        logger.error(f"Error getting market context: {e}")
        return {'error': str(e)}


def get_trading_history_summary(order_manager, accounts: List[str]) -> Dict[str, Any]:
    """Get trading history summary for AI analysis"""
    try:
        summary = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'best_pairs': {},
            'worst_pairs': {},
            'recent_performance': []
        }
        
        for account_id in accounts:
            try:
                trades = order_manager.get_trades(account_id)
                if trades:
                    for trade in trades:
                        if hasattr(trade, 'status') and trade.status == 'CLOSED':
                            summary['total_trades'] += 1
                            if hasattr(trade, 'unrealized_pl') and trade.unrealized_pl > 0:
                                summary['winning_trades'] += 1
                            else:
                                summary['losing_trades'] += 1
            except Exception:
                continue
        
        if summary['total_trades'] > 0:
            summary['win_rate'] = summary['winning_trades'] / summary['total_trades']
        
        return summary
    except Exception as e:
        logger.error(f"Error getting trading history: {e}")
        return {'error': str(e)}


def get_strategy_performance(shadow_system=None) -> Dict[str, Any]:
    """Get strategy performance summary"""
    try:
        if not shadow_system:
            return {'error': 'Shadow system not available'}
        
        performance = shadow_system.get_strategy_performance()
        if not performance:
            return {'error': 'No performance data available'}
        
        summary = {}
        for strategy_name, perf in performance.items():
            summary[strategy_name] = {
                'total_signals': perf.total_signals,
                'daily_signals': perf.daily_signals,
                'max_daily_signals': perf.max_daily_signals,
                'utilization': perf.daily_signals / perf.max_daily_signals if perf.max_daily_signals > 0 else 0
            }
        
        return summary
    except Exception as e:
        logger.error(f"Error getting strategy performance: {e}")
        return {'error': str(e)}


def get_gold_specific_analysis(data_feed, accounts: List[str]) -> Dict[str, Any]:
    """Get dedicated Gold/XAU_USD analysis"""
    try:
        gold_data = {}
        for account_id in accounts:
            try:
                market = data_feed.get_market_data(account_id)
                if market and 'XAU_USD' in market:
                    xau_data = market['XAU_USD']
                    gold_data = {
                        'current_price': (xau_data.bid + xau_data.ask) / 2,
                        'bid': xau_data.bid,
                        'ask': xau_data.ask,
                        'spread': xau_data.spread,
                        'timestamp': xau_data.timestamp,
                        'is_live': xau_data.is_live,
                        'volatility_score': getattr(xau_data, 'volatility_score', None)
                    }
                    break
            except Exception:
                continue
        
        # Add Gold-specific analysis
        if gold_data:
            gold_data.update({
                'session_analysis': _analyze_gold_session(),
                'support_resistance': _get_gold_levels(gold_data.get('current_price', 0)),
                'news_impact': _get_gold_news_impact()
            })
        
        return gold_data
    except Exception as e:
        logger.error(f"Error getting Gold analysis: {e}")
        return {'error': str(e)}


def _get_current_trading_session() -> Dict[str, Any]:
    """Get current trading session information"""
    now_utc = datetime.now(timezone.utc)
    hour = now_utc.hour
    
    sessions = {
        'Tokyo': {'start': 0, 'end': 9, 'volatility': 0.8, 'pairs': ['USD_JPY', 'AUD_JPY']},
        'London': {'start': 8, 'end': 17, 'volatility': 1.5, 'pairs': ['EUR_USD', 'GBP_USD', 'XAU_USD']},
        'New York': {'start': 13, 'end': 22, 'volatility': 1.2, 'pairs': ['EUR_USD', 'GBP_USD', 'USD_CAD', 'XAU_USD']}
    }
    
    active_sessions = []
    for name, config in sessions.items():
        if config['start'] <= hour < config['end']:
            active_sessions.append(name)
    
    return {
        'current_time': now_utc.strftime("%H:%M:%S UTC"),
        'active_sessions': active_sessions,
        'sessions': sessions
    }


def _analyze_volatility(data_feed, accounts: List[str]) -> Dict[str, Any]:
    """Analyze market volatility across instruments"""
    try:
        volatility_scores = {}
        for account_id in accounts:
            try:
                market = data_feed.get_market_data(account_id)
                if market:
                    for instrument, data in market.items():
                        if hasattr(data, 'volatility_score') and data.volatility_score:
                            volatility_scores[instrument] = data.volatility_score
            except Exception:
                continue
        
        if volatility_scores:
            avg_volatility = sum(volatility_scores.values()) / len(volatility_scores)
            high_vol_pairs = [pair for pair, vol in volatility_scores.items() if vol > avg_volatility * 1.2]
            
            return {
                'average_volatility': avg_volatility,
                'high_volatility_pairs': high_vol_pairs,
                'scores': volatility_scores
            }
        
        return {'error': 'No volatility data available'}
    except Exception as e:
        return {'error': str(e)}


def _get_news_sentiment() -> Dict[str, Any]:
    """Get current news sentiment (placeholder for news integration)"""
    return {
        'overall_sentiment': 'neutral',
        'forex_sentiment': 'neutral',
        'gold_sentiment': 'neutral',
        'last_update': datetime.now(timezone.utc).isoformat()
    }


def _get_upcoming_events() -> List[Dict[str, Any]]:
    """Get upcoming economic events (placeholder for calendar integration)"""
    return [
        {
            'event': 'Sample Economic Event',
            'time': '14:00 UTC',
            'impact': 'high',
            'currency': 'USD'
        }
    ]


def _analyze_gold_session() -> Dict[str, Any]:
    """Analyze Gold trading session characteristics"""
    now_utc = datetime.now(timezone.utc)
    hour = now_utc.hour
    
    if 8 <= hour < 17:  # London session
        return {'session': 'London', 'volatility': 'high', 'recommendation': 'Active trading period'}
    elif 13 <= hour < 22:  # NY session
        return {'session': 'New York', 'volatility': 'medium', 'recommendation': 'Good liquidity'}
    else:
        return {'session': 'Asian', 'volatility': 'low', 'recommendation': 'Lower activity'}


def _get_gold_levels(current_price: float) -> Dict[str, float]:
    """Get Gold support/resistance levels"""
    if current_price == 0:
        return {}
    
    # Simple level calculation (in practice, use more sophisticated analysis)
    return {
        'support_1': current_price * 0.995,
        'support_2': current_price * 0.990,
        'resistance_1': current_price * 1.005,
        'resistance_2': current_price * 1.010
    }


def _get_gold_news_impact() -> Dict[str, Any]:
    """Get Gold-specific news impact analysis"""
    return {
        'impact': 'neutral',
        'factors': ['USD strength', 'Inflation data', 'Fed policy'],
        'sentiment': 'mixed'
    }
