#!/usr/bin/env python3
"""
Live Trading to Backtesting Feedback System

Captures live trading data and exports it back to backtesting system for:
1. Strategy performance validation (backtest vs live)
2. Real slippage and spread data
3. Actual execution quality
4. Market condition patterns
5. Strategy improvement recommendations

This creates a continuous improvement loop!
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import os

logger = logging.getLogger(__name__)


@dataclass
class LiveTradeData:
    """Live trade execution data"""
    timestamp: str
    instrument: str
    side: str  # BUY or SELL
    
    # Entry data
    entry_price: float
    entry_time: str
    planned_entry: float  # What strategy wanted
    actual_entry: float   # What we got (slippage!)
    entry_slippage: float  # Difference
    
    # Exit data
    exit_price: Optional[float]
    exit_time: Optional[str]
    planned_exit: Optional[float]
    actual_exit: Optional[float]
    exit_slippage: Optional[float]
    exit_reason: Optional[str]  # TP, SL, Signal, Manual
    
    # Position data
    position_size: int
    risk_amount: float
    stop_loss: float
    take_profit: float
    
    # Spread data
    entry_spread: float
    avg_spread_during_trade: float
    max_spread_seen: float
    
    # Performance
    profit_loss: Optional[float]
    profit_loss_pct: Optional[float]
    win: Optional[bool]
    duration_minutes: Optional[int]
    
    # Strategy data
    strategy_name: str
    signal_confidence: float
    ema_fast: Optional[float]
    ema_mid: Optional[float]
    ema_slow: Optional[float]
    rsi: Optional[float]
    atr: Optional[float]
    
    # Market conditions at entry
    volatility_score: float
    market_regime: str  # trending, ranging
    session: str  # london, ny, asian
    day_of_week: str
    
    # Account data
    account_id: str
    account_balance_at_entry: float
    account_balance_at_exit: Optional[float]


@dataclass
class StrategyPerformanceComparison:
    """Comparison of backtest vs live performance"""
    strategy_name: str
    instrument: str
    timeframe: str
    
    # Backtested metrics
    backtest_sharpe: float
    backtest_win_rate: float
    backtest_avg_win: float
    backtest_avg_loss: float
    backtest_total_trades: int
    
    # Live metrics
    live_sharpe: Optional[float]
    live_win_rate: Optional[float]
    live_avg_win: Optional[float]
    live_avg_loss: Optional[float]
    live_total_trades: int
    live_period_days: int
    
    # Performance gap
    sharpe_difference: Optional[float]
    win_rate_difference: Optional[float]
    avg_win_difference: Optional[float]
    
    # Recommendations
    performance_grade: str  # EXCEEDING, MEETING, BELOW, FAILING
    recommendations: List[str]
    
    # Validation
    sample_size_adequate: bool  # >30 trades minimum
    statistical_confidence: float


@dataclass
class MarketConditionPattern:
    """Market condition patterns from live trading"""
    session: str
    day_of_week: str
    avg_volatility: float
    avg_spread: float
    market_regime: str
    
    # Performance in this condition
    trades_count: int
    win_rate: float
    avg_profit: float
    
    # Recommendations
    trade_this_condition: bool
    recommended_confidence_adjustment: float
    notes: str


class LiveToBacktestFeedback:
    """
    Collects live trading data and exports feedback to backtesting system
    
    Key outputs:
    1. Live trade database (for comparison)
    2. Performance comparison reports
    3. Slippage/spread statistics
    4. Market condition analysis
    5. Strategy improvement recommendations
    """
    
    def __init__(self, export_path: str = None):
        self.name = "LiveToBacktestFeedback"
        
        # Export location (Google Drive)
        if export_path is None:
            export_path = "/Users/mac/Library/CloudStorage/GoogleDrive-fxgdesigns1@gmail.com/My Drive/AI Trading/live_trading_feedback"
        
        self.export_path = export_path
        
        # Data storage
        self.live_trades: List[LiveTradeData] = []
        self.performance_comparisons: List[StrategyPerformanceComparison] = []
        self.condition_patterns: List[MarketConditionPattern] = []
        
        # Ensure export directory exists
        os.makedirs(export_path, exist_ok=True)
        
        logger.info(f"✅ {self.name} initialized")
        logger.info(f"   Export path: {export_path}")
    
    def record_trade_entry(
        self,
        instrument: str,
        side: str,
        planned_price: float,
        actual_price: float,
        position_size: int,
        stop_loss: float,
        take_profit: float,
        strategy_name: str,
        confidence: float,
        market_data: Dict,
        account_id: str,
        account_balance: float
    ) -> str:
        """
        Record a trade entry for later analysis
        
        Returns:
            trade_id for tracking
        """
        
        entry_spread = abs(actual_price - planned_price)
        
        trade = LiveTradeData(
            timestamp=datetime.now().isoformat(),
            instrument=instrument,
            side=side,
            entry_price=actual_price,
            entry_time=datetime.now().isoformat(),
            planned_entry=planned_price,
            actual_entry=actual_price,
            entry_slippage=entry_spread,
            exit_price=None,
            exit_time=None,
            planned_exit=None,
            actual_exit=None,
            exit_slippage=None,
            exit_reason=None,
            position_size=position_size,
            risk_amount=0,  # Calculate based on stop
            stop_loss=stop_loss,
            take_profit=take_profit,
            entry_spread=entry_spread,
            avg_spread_during_trade=entry_spread,
            max_spread_seen=entry_spread,
            profit_loss=None,
            profit_loss_pct=None,
            win=None,
            duration_minutes=None,
            strategy_name=strategy_name,
            signal_confidence=confidence,
            ema_fast=market_data.get('ema_3'),
            ema_mid=market_data.get('ema_8'),
            ema_slow=market_data.get('ema_21'),
            rsi=market_data.get('rsi'),
            atr=market_data.get('atr'),
            volatility_score=market_data.get('volatility_score', 0.5),
            market_regime=market_data.get('regime', 'unknown'),
            session=self._get_session(),
            day_of_week=datetime.now().strftime('%A'),
            account_id=account_id,
            account_balance_at_entry=account_balance,
            account_balance_at_exit=None
        )
        
        self.live_trades.append(trade)
        
        trade_id = f"{instrument}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"📊 Trade recorded: {trade_id}")
        logger.info(f"   Entry: {actual_price:.5f} (planned: {planned_price:.5f})")
        logger.info(f"   Slippage: {entry_spread:.5f}")
        
        return trade_id
    
    def record_trade_exit(
        self,
        trade_id: str,
        exit_price: float,
        exit_reason: str,
        account_balance: float
    ):
        """Record trade exit and calculate performance"""
        
        # Find the trade (simplified - would use trade_id in production)
        if not self.live_trades:
            logger.warning(f"⚠️ No trade found for exit recording")
            return
        
        trade = self.live_trades[-1]  # Most recent
        
        trade.exit_price = exit_price
        trade.exit_time = datetime.now().isoformat()
        trade.actual_exit = exit_price
        trade.exit_reason = exit_reason
        trade.account_balance_at_exit = account_balance
        
        # Calculate performance
        entry_time = datetime.fromisoformat(trade.entry_time)
        exit_time = datetime.now()
        trade.duration_minutes = int((exit_time - entry_time).total_seconds() / 60)
        
        if trade.side == 'BUY':
            trade.profit_loss = (exit_price - trade.entry_price) * trade.position_size
        else:
            trade.profit_loss = (trade.entry_price - exit_price) * trade.position_size
        
        trade.profit_loss_pct = (trade.profit_loss / trade.account_balance_at_entry) * 100
        trade.win = trade.profit_loss > 0
        
        logger.info(f"📊 Trade closed: {trade.instrument}")
        logger.info(f"   P/L: ${trade.profit_loss:.2f} ({trade.profit_loss_pct:+.2f}%)")
        logger.info(f"   Duration: {trade.duration_minutes} minutes")
        logger.info(f"   Result: {'WIN ✅' if trade.win else 'LOSS ❌'}")
    
    def _get_session(self) -> str:
        """Determine current trading session"""
        hour = datetime.now().hour
        if 0 <= hour < 8:
            return 'asian'
        elif 8 <= hour < 13:
            return 'london'
        elif 13 <= hour < 17:
            return 'ny_overlap'
        else:
            return 'ny_afternoon'
    
    def generate_backtest_feedback(self) -> Dict:
        """
        Generate comprehensive feedback for backtesting system
        
        Returns dict with:
        - Real slippage data
        - Actual spread statistics
        - Win rates by session/condition
        - Strategy performance vs backtest
        - Improvement recommendations
        """
        
        if not self.live_trades:
            return {
                'status': 'no_data',
                'message': 'No live trades recorded yet'
            }
        
        # Separate wins and losses
        closed_trades = [t for t in self.live_trades if t.profit_loss is not None]
        wins = [t for t in closed_trades if t.win]
        losses = [t for t in closed_trades if not t.win]
        
        if not closed_trades:
            return {
                'status': 'no_closed_trades',
                'message': 'No closed trades yet'
            }
        
        # Calculate statistics
        feedback = {
            'collection_period': {
                'start': self.live_trades[0].timestamp if self.live_trades else None,
                'end': datetime.now().isoformat(),
                'days': self._calculate_days_trading(),
                'total_trades': len(closed_trades)
            },
            
            'performance_summary': {
                'total_trades': len(closed_trades),
                'winning_trades': len(wins),
                'losing_trades': len(losses),
                'win_rate': (len(wins) / len(closed_trades) * 100) if closed_trades else 0,
                'avg_win': sum(t.profit_loss for t in wins) / len(wins) if wins else 0,
                'avg_loss': sum(t.profit_loss for t in losses) / len(losses) if losses else 0,
                'avg_win_pct': sum(t.profit_loss_pct for t in wins) / len(wins) if wins else 0,
                'avg_loss_pct': sum(t.profit_loss_pct for t in losses) / len(losses) if losses else 0,
                'profit_factor': abs(sum(t.profit_loss for t in wins) / sum(t.profit_loss for t in losses)) if losses and wins else 0,
                'total_pl': sum(t.profit_loss for t in closed_trades)
            },
            
            'execution_quality': {
                'avg_entry_slippage': sum(t.entry_slippage for t in self.live_trades) / len(self.live_trades),
                'max_entry_slippage': max(t.entry_slippage for t in self.live_trades),
                'avg_spread': sum(t.entry_spread for t in self.live_trades) / len(self.live_trades),
                'max_spread': max(t.max_spread_seen for t in self.live_trades),
                'avg_fill_quality': self._calculate_fill_quality()
            },
            
            'session_analysis': self._analyze_by_session(closed_trades),
            'day_of_week_analysis': self._analyze_by_day(closed_trades),
            'condition_analysis': self._analyze_by_condition(closed_trades),
            'strategy_breakdown': self._analyze_by_strategy(closed_trades),
            
            'backtest_validation': self._compare_to_backtest(),
            
            'recommendations': self._generate_recommendations(closed_trades)
        }
        
        return feedback
    
    def _calculate_days_trading(self) -> int:
        """Calculate days since first trade"""
        if not self.live_trades:
            return 0
        
        first = datetime.fromisoformat(self.live_trades[0].timestamp)
        now = datetime.now()
        return (now - first).days + 1
    
    def _calculate_fill_quality(self) -> float:
        """
        Calculate overall fill quality (0-1)
        1.0 = perfect fills (no slippage)
        0.0 = terrible fills
        """
        if not self.live_trades:
            return 0
        
        total_slippage = sum(t.entry_slippage for t in self.live_trades)
        avg_slippage = total_slippage / len(self.live_trades)
        
        # Score: 0.5 pips = excellent (1.0), 2.0 pips = poor (0.5), 5+ pips = terrible (0.2)
        if avg_slippage < 0.0005:
            return 1.0
        elif avg_slippage < 0.001:
            return 0.9
        elif avg_slippage < 0.002:
            return 0.7
        elif avg_slippage < 0.005:
            return 0.5
        else:
            return 0.3
    
    def _analyze_by_session(self, trades: List[LiveTradeData]) -> Dict:
        """Analyze performance by trading session"""
        sessions = {}
        
        for trade in trades:
            session = trade.session
            if session not in sessions:
                sessions[session] = {'trades': [], 'wins': 0, 'total_pl': 0}
            
            sessions[session]['trades'].append(trade)
            if trade.win:
                sessions[session]['wins'] += 1
            sessions[session]['total_pl'] += trade.profit_loss
        
        analysis = {}
        for session, data in sessions.items():
            total = len(data['trades'])
            analysis[session] = {
                'trades': total,
                'win_rate': (data['wins'] / total * 100) if total else 0,
                'avg_pl': data['total_pl'] / total if total else 0,
                'total_pl': data['total_pl'],
                'recommendation': 'TRADE' if (data['wins'] / total) > 0.6 else 'AVOID' if total > 10 else 'MORE_DATA'
            }
        
        return analysis
    
    def _analyze_by_day(self, trades: List[LiveTradeData]) -> Dict:
        """Analyze performance by day of week"""
        days = {}
        
        for trade in trades:
            day = trade.day_of_week
            if day not in days:
                days[day] = {'trades': [], 'wins': 0, 'total_pl': 0}
            
            days[day]['trades'].append(trade)
            if trade.win:
                days[day]['wins'] += 1
            days[day]['total_pl'] += trade.profit_loss
        
        analysis = {}
        for day, data in days.items():
            total = len(data['trades'])
            analysis[day] = {
                'trades': total,
                'win_rate': (data['wins'] / total * 100) if total else 0,
                'avg_pl': data['total_pl'] / total if total else 0,
                'total_pl': data['total_pl']
            }
        
        return analysis
    
    def _analyze_by_condition(self, trades: List[LiveTradeData]) -> Dict:
        """Analyze performance by market conditions"""
        conditions = {}
        
        for trade in trades:
            # Classify condition
            vol = trade.volatility_score
            regime = trade.market_regime
            
            if vol > 0.7:
                cond = f"{regime}_high_vol"
            elif vol > 0.4:
                cond = f"{regime}_medium_vol"
            else:
                cond = f"{regime}_low_vol"
            
            if cond not in conditions:
                conditions[cond] = {'trades': [], 'wins': 0, 'total_pl': 0}
            
            conditions[cond]['trades'].append(trade)
            if trade.win:
                conditions[cond]['wins'] += 1
            conditions[cond]['total_pl'] += trade.profit_loss
        
        analysis = {}
        for cond, data in conditions.items():
            total = len(data['trades'])
            win_rate = (data['wins'] / total * 100) if total else 0
            
            analysis[cond] = {
                'trades': total,
                'win_rate': win_rate,
                'avg_pl': data['total_pl'] / total if total else 0,
                'recommendation': 'EXCELLENT' if win_rate > 70 else 'GOOD' if win_rate > 60 else 'AVOID'
            }
        
        return analysis
    
    def _analyze_by_strategy(self, trades: List[LiveTradeData]) -> Dict:
        """Analyze performance by strategy"""
        strategies = {}
        
        for trade in trades:
            strat = trade.strategy_name
            if strat not in strategies:
                strategies[strat] = {'trades': [], 'wins': 0, 'total_pl': 0, 'by_instrument': {}}
            
            strategies[strat]['trades'].append(trade)
            if trade.win:
                strategies[strat]['wins'] += 1
            strategies[strat]['total_pl'] += trade.profit_loss
            
            # By instrument
            inst = trade.instrument
            if inst not in strategies[strat]['by_instrument']:
                strategies[strat]['by_instrument'][inst] = {'trades': 0, 'wins': 0, 'pl': 0}
            
            strategies[strat]['by_instrument'][inst]['trades'] += 1
            if trade.win:
                strategies[strat]['by_instrument'][inst]['wins'] += 1
            strategies[strat]['by_instrument'][inst]['pl'] += trade.profit_loss
        
        analysis = {}
        for strat, data in strategies.items():
            total = len(data['trades'])
            
            inst_performance = {}
            for inst, inst_data in data['by_instrument'].items():
                inst_total = inst_data['trades']
                inst_performance[inst] = {
                    'trades': inst_total,
                    'win_rate': (inst_data['wins'] / inst_total * 100) if inst_total else 0,
                    'total_pl': inst_data['pl']
                }
            
            analysis[strat] = {
                'trades': total,
                'win_rate': (data['wins'] / total * 100) if total else 0,
                'avg_pl': data['total_pl'] / total if total else 0,
                'total_pl': data['total_pl'],
                'by_instrument': inst_performance
            }
        
        return analysis
    
    def _compare_to_backtest(self) -> Dict:
        """Compare live performance to backtested expectations"""
        
        # This would load backtested results and compare
        # For now, return structure
        
        comparisons = {
            'note': 'Load from exported strategies for comparison',
            'backtest_data_location': '/Users/mac/Library/CloudStorage/GoogleDrive-fxgdesigns1@gmail.com/My Drive/AI Trading/exported strategies',
            'comparisons': []
        }
        
        return comparisons
    
    def _generate_recommendations(self, trades: List[LiveTradeData]) -> List[str]:
        """Generate strategy improvement recommendations"""
        recommendations = []
        
        if not trades:
            return ["Not enough data yet - need at least 10 trades"]
        
        # Win rate analysis
        wins = [t for t in trades if t.win]
        win_rate = len(wins) / len(trades) * 100
        
        if win_rate < 50:
            recommendations.append("CRITICAL: Win rate below 50% - Review entry criteria")
        elif win_rate < 60:
            recommendations.append("WARNING: Win rate below 60% - Consider tightening filters")
        elif win_rate > 80:
            recommendations.append("EXCELLENT: Win rate above 80% - Strategy performing well")
        
        # Slippage analysis
        avg_slippage = sum(t.entry_slippage for t in trades) / len(trades)
        if avg_slippage > 0.002:
            recommendations.append("HIGH SLIPPAGE: Average slippage >2 pips - Consider limit orders")
        
        # Session analysis
        session_data = self._analyze_by_session(trades)
        best_session = max(session_data.items(), key=lambda x: x[1]['win_rate']) if session_data else None
        if best_session:
            recommendations.append(f"BEST SESSION: {best_session[0]} with {best_session[1]['win_rate']:.1f}% win rate")
        
        # Duration analysis
        durations = [t.duration_minutes for t in trades if t.duration_minutes]
        if durations:
            avg_duration = sum(durations) / len(durations)
            if avg_duration > 120:
                recommendations.append(f"LONG HOLDS: Average {avg_duration:.0f} min - Consider tighter profit targets")
        
        return recommendations
    
    def export_to_backtesting_system(self) -> str:
        """
        Export all feedback data to backtesting system location
        
        Returns:
            Path to exported file
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Generate complete feedback
        feedback = self.generate_backtest_feedback()
        
        # Export to JSON
        export_file = os.path.join(
            self.export_path,
            f"live_trading_feedback_{timestamp}.json"
        )
        
        with open(export_file, 'w') as f:
            json.dump(feedback, f, indent=2)
        
        logger.info(f"✅ Feedback exported to: {export_file}")
        
        # Also export raw trades
        trades_file = os.path.join(
            self.export_path,
            f"live_trades_{timestamp}.json"
        )
        
        trades_data = [asdict(t) for t in self.live_trades]
        with open(trades_file, 'w') as f:
            json.dump(trades_data, f, indent=2)
        
        logger.info(f"✅ Raw trades exported to: {trades_file}")
        
        # Create summary report
        summary_file = os.path.join(
            self.export_path,
            f"FEEDBACK_SUMMARY_{timestamp}.md"
        )
        
        self._create_summary_report(feedback, summary_file)
        
        return export_file
    
    def _create_summary_report(self, feedback: Dict, output_file: str):
        """Create human-readable summary report"""
        
        with open(output_file, 'w') as f:
            f.write("# LIVE TRADING FEEDBACK REPORT\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("---\n\n")
            
            # Performance summary
            perf = feedback.get('performance_summary', {})
            f.write("## 📊 PERFORMANCE SUMMARY\n\n")
            f.write(f"- **Total Trades:** {perf.get('total_trades', 0)}\n")
            f.write(f"- **Win Rate:** {perf.get('win_rate', 0):.1f}%\n")
            f.write(f"- **Average Win:** ${perf.get('avg_win', 0):.2f} ({perf.get('avg_win_pct', 0):.2f}%)\n")
            f.write(f"- **Average Loss:** ${perf.get('avg_loss', 0):.2f} ({perf.get('avg_loss_pct', 0):.2f}%)\n")
            f.write(f"- **Profit Factor:** {perf.get('profit_factor', 0):.2f}\n")
            f.write(f"- **Total P/L:** ${perf.get('total_pl', 0):.2f}\n\n")
            
            # Execution quality
            exec_quality = feedback.get('execution_quality', {})
            f.write("## 🎯 EXECUTION QUALITY\n\n")
            f.write(f"- **Average Slippage:** {exec_quality.get('avg_entry_slippage', 0)*10000:.2f} pips\n")
            f.write(f"- **Max Slippage:** {exec_quality.get('max_entry_slippage', 0)*10000:.2f} pips\n")
            f.write(f"- **Average Spread:** {exec_quality.get('avg_spread', 0)*10000:.2f} pips\n")
            f.write(f"- **Fill Quality Score:** {exec_quality.get('avg_fill_quality', 0):.1%}\n\n")
            
            # Recommendations
            recs = feedback.get('recommendations', [])
            if recs:
                f.write("## 💡 RECOMMENDATIONS FOR BACKTESTING\n\n")
                for i, rec in enumerate(recs, 1):
                    f.write(f"{i}. {rec}\n")
            
            f.write("\n---\n\n")
            f.write("**Use this data to improve backtesting assumptions and strategy parameters!**\n")
        
        logger.info(f"✅ Summary report created: {output_file}")


# Global instance
_feedback_system = None

def get_feedback_system() -> LiveToBacktestFeedback:
    """Get global feedback system instance"""
    global _feedback_system
    if _feedback_system is None:
        _feedback_system = LiveToBacktestFeedback()
    return _feedback_system


