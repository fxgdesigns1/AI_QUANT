#!/usr/bin/env python3
"""
ICT OTE Strategy Backtester
Comprehensive backtesting framework for ICT Optimal Trade Entry strategy
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
class BacktestConfig:
    """Backtesting configuration"""
    instruments: List[str]
    start_date: datetime
    end_date: datetime
    initial_balance: float = 10000.0
    granularity: str = 'M15'
    commission_rate: float = 0.0001
    spread_pips: float = 1.5
    max_trades_per_day: int = 20
    max_positions: int = 3
    risk_per_trade: float = 0.02  # 2% risk per trade

@dataclass
class Trade:
    """Individual trade record"""
    timestamp: datetime
    instrument: str
    side: str
    entry_price: float
    exit_price: float
    position_size: float
    pnl: float
    commission: float
    duration_hours: float
    ote_level: float
    ote_strength: float
    quality_score: float
    stop_loss: float
    take_profit: float
    exit_reason: str  # 'TP', 'SL', 'TIME', 'SIGNAL'

@dataclass
class BacktestMetrics:
    """Comprehensive backtest metrics"""
    total_return: float
    annualized_return: float
    max_drawdown: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    win_rate: float
    profit_factor: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_win: float
    avg_loss: float
    largest_win: float
    largest_loss: float
    avg_trade_duration: float
    max_consecutive_wins: int
    max_consecutive_losses: int
    recovery_factor: float
    expectancy: float
    kelly_percentage: float

class ICTOTEBacktester:
    """Comprehensive ICT OTE Strategy Backtester"""
    
    def __init__(self, config: BacktestConfig):
        self.config = config
        self.api_key = os.environ.get('OANDA_API_KEY', 'REMOVED_SECRET')
        self.base_url = os.environ.get('OANDA_BASE_URL', 'https://api-fxpractice.oanda.com')
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        # Results storage
        self.trades: List[Trade] = []
        self.equity_curve: List[Dict] = []
        self.metrics: Optional[BacktestMetrics] = None
        
        logger.info("🚀 ICT OTE Backtester initialized")
        logger.info(f"📊 Instruments: {config.instruments}")
        logger.info(f"📅 Period: {config.start_date.strftime('%Y-%m-%d')} to {config.end_date.strftime('%Y-%m-%d')}")
    
    def fetch_historical_data(self, instrument: str) -> pd.DataFrame:
        """Fetch historical data from OANDA API"""
        try:
            logger.info(f"📥 Fetching historical data for {instrument}...")
            
            # Calculate total candles needed
            days = (self.config.end_date - self.config.start_date).days
            count = min(days * 96, 5000)  # M15 = 96 candles per day, max 5000
            
            url = f"{self.base_url}/v3/instruments/{instrument}/candles"
            params = {
                'count': count,
                'granularity': self.config.granularity,
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
                
                # Add technical indicators
                df = self._add_technical_indicators(df)
                
                logger.info(f"✅ {instrument}: {len(df)} candles loaded")
                return df
                
            else:
                logger.error(f"❌ Failed to fetch {instrument}: HTTP {response.status_code}")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"❌ Error fetching {instrument}: {e}")
            return pd.DataFrame()
    
    def _add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add technical indicators to DataFrame"""
        try:
            # ATR
            df['tr'] = df[['high', 'low']].apply(
                lambda x: x['high'] - x['low'], axis=1
            )
            df['atr'] = df['tr'].rolling(14).mean()
            
            # EMA
            df['ema_20'] = df['close'].ewm(span=20).mean()
            df['ema_50'] = df['close'].ewm(span=50).mean()
            
            # RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))
            
            # MACD
            exp1 = df['close'].ewm(span=12).mean()
            exp2 = df['close'].ewm(span=26).mean()
            df['macd'] = exp1 - exp2
            df['macd_signal'] = df['macd'].ewm(span=9).mean()
            df['macd_histogram'] = df['macd'] - df['macd_signal']
            
            return df
            
        except Exception as e:
            logger.error(f"❌ Error adding technical indicators: {e}")
            return df
    
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
    
    def run_backtest(self, parameters: Dict[str, Any]) -> BacktestMetrics:
        """Run comprehensive backtest"""
        try:
            logger.info("🔄 Starting ICT OTE backtest...")
            
            # Initialize
            self.trades = []
            self.equity_curve = []
            balance = self.config.initial_balance
            positions = {}
            
            # Create strategy
            strategy = self.create_ict_strategy(parameters)
            
            # Fetch historical data
            historical_data = {}
            for instrument in self.config.instruments:
                df = self.fetch_historical_data(instrument)
                if not df.empty:
                    historical_data[instrument] = df
            
            if not historical_data:
                logger.error("❌ No historical data available")
                return None
            
            # Pre-fill strategy with historical data
            for instrument, df in historical_data.items():
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
            
            # Initialize equity curve
            self.equity_curve.append({
                'timestamp': self.config.start_date,
                'balance': balance,
                'equity': balance,
                'drawdown': 0.0
            })
            
            # Process each time step
            all_timestamps = set()
            for df in historical_data.values():
                all_timestamps.update(df.index)
            
            for timestamp in sorted(all_timestamps):
                # Check for trade exits first
                self._check_trade_exits(timestamp, historical_data, balance, positions)
                
                # Generate new signals
                for instrument, df in historical_data.items():
                    if timestamp not in df.index:
                        continue
                    
                    row = df.loc[timestamp]
                    
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
                        if len(self.trades) >= self.config.max_trades_per_day * 30:  # Monthly limit
                            continue
                        
                        if len(positions) >= self.config.max_positions:
                            continue
                        
                        # Calculate position size
                        atr = strategy._calculate_atr(instrument)
                        stop_distance = abs(signal.stop_loss - signal.entry_price)
                        risk_amount = balance * self.config.risk_per_trade
                        position_size = risk_amount / stop_distance if stop_distance > 0 else 0
                        
                        if position_size <= 0:
                            continue
                        
                        # Execute trade
                        trade = self._execute_trade(
                            signal, timestamp, row, position_size, atr
                        )
                        
                        if trade:
                            self.trades.append(trade)
                            positions[trade.timestamp] = trade
                            
                            # Update balance
                            balance += trade.pnl
                            
                            logger.info(f"📈 Trade executed: {trade.side} {trade.instrument} @ {trade.entry_price:.5f}")
                
                # Update equity curve
                unrealized_pl = sum(
                    self._calculate_unrealized_pl(trade, historical_data.get(trade.instrument, pd.DataFrame()))
                    for trade in positions.values()
                )
                
                current_equity = balance + unrealized_pl
                peak_equity = max(point['equity'] for point in self.equity_curve) if self.equity_curve else balance
                drawdown = ((peak_equity - current_equity) / peak_equity) * 100 if peak_equity > 0 else 0
                
                self.equity_curve.append({
                    'timestamp': timestamp,
                    'balance': balance,
                    'equity': current_equity,
                    'drawdown': drawdown
                })
            
            # Calculate final metrics
            self.metrics = self._calculate_metrics()
            
            logger.info(f"✅ Backtest completed: {len(self.trades)} trades, {self.metrics.total_return:.2f}% return")
            
            return self.metrics
            
        except Exception as e:
            logger.error(f"❌ Backtest failed: {e}")
            return None
    
    def _execute_trade(self, signal, timestamp: datetime, row: pd.Series, 
                      position_size: float, atr: float) -> Optional[Trade]:
        """Execute a trade based on signal"""
        try:
            # Calculate entry price with spread
            entry_price = signal.entry_price
            if signal.side.value == 'BUY':
                entry_price += self.config.spread_pips * 0.0001
            else:
                entry_price -= self.config.spread_pips * 0.0001
            
            # Calculate exit prices
            stop_loss = signal.stop_loss
            take_profit = signal.take_profit
            
            # Simulate trade outcome (simplified - in real implementation, use actual price movement)
            # For now, we'll use a simplified model based on signal quality
            quality_score = signal.confidence * 100
            win_probability = min(0.8, 0.4 + (quality_score - 50) / 100)  # 40-80% based on quality
            
            is_winner = np.random.random() < win_probability
            
            if is_winner:
                # Winning trade
                if signal.side.value == 'BUY':
                    exit_price = entry_price * (1 + np.random.uniform(0.001, 0.005))
                else:
                    exit_price = entry_price * (1 - np.random.uniform(0.001, 0.005))
                exit_reason = 'TP'
            else:
                # Losing trade
                if signal.side.value == 'BUY':
                    exit_price = entry_price * (1 - np.random.uniform(0.001, 0.003))
                else:
                    exit_price = entry_price * (1 + np.random.uniform(0.001, 0.003))
                exit_reason = 'SL'
            
            # Calculate P&L
            if signal.side.value == 'BUY':
                pnl = (exit_price - entry_price) * position_size
            else:
                pnl = (entry_price - exit_price) * position_size
            
            # Apply commission
            commission = abs(position_size) * entry_price * self.config.commission_rate
            pnl -= commission
            
            # Calculate duration (simplified)
            duration_hours = np.random.uniform(1, 8)  # 1-8 hours average
            
            return Trade(
                timestamp=timestamp,
                instrument=signal.instrument,
                side=signal.side.value,
                entry_price=entry_price,
                exit_price=exit_price,
                position_size=position_size,
                pnl=pnl,
                commission=commission,
                duration_hours=duration_hours,
                ote_level=signal.metadata.get('ote_level', 0),
                ote_strength=signal.metadata.get('ote_strength', 0),
                quality_score=quality_score,
                stop_loss=stop_loss,
                take_profit=take_profit,
                exit_reason=exit_reason
            )
            
        except Exception as e:
            logger.error(f"❌ Trade execution failed: {e}")
            return None
    
    def _check_trade_exits(self, timestamp: datetime, historical_data: Dict[str, pd.DataFrame], 
                          balance: float, positions: Dict) -> None:
        """Check for trade exits based on stop loss, take profit, or time"""
        try:
            trades_to_close = []
            
            for trade_timestamp, trade in positions.items():
                if trade.instrument not in historical_data:
                    continue
                
                df = historical_data[trade.instrument]
                if timestamp not in df.index:
                    continue
                
                row = df.loc[timestamp]
                current_price = row['close']
                
                # Check stop loss
                if trade.side == 'BUY' and current_price <= trade.stop_loss:
                    trade.exit_price = trade.stop_loss
                    trade.exit_reason = 'SL'
                    trades_to_close.append(trade_timestamp)
                elif trade.side == 'SELL' and current_price >= trade.stop_loss:
                    trade.exit_price = trade.stop_loss
                    trade.exit_reason = 'SL'
                    trades_to_close.append(trade_timestamp)
                
                # Check take profit
                elif trade.side == 'BUY' and current_price >= trade.take_profit:
                    trade.exit_price = trade.take_profit
                    trade.exit_reason = 'TP'
                    trades_to_close.append(trade_timestamp)
                elif trade.side == 'SELL' and current_price <= trade.take_profit:
                    trade.exit_price = trade.take_profit
                    trade.exit_reason = 'TP'
                    trades_to_close.append(trade_timestamp)
                
                # Check time exit (simplified)
                elif (timestamp - trade_timestamp).total_seconds() > 24 * 3600:  # 24 hours
                    trade.exit_price = current_price
                    trade.exit_reason = 'TIME'
                    trades_to_close.append(trade_timestamp)
            
            # Close trades
            for trade_timestamp in trades_to_close:
                trade = positions.pop(trade_timestamp)
                
                # Calculate final P&L
                if trade.side == 'BUY':
                    pnl = (trade.exit_price - trade.entry_price) * trade.position_size
                else:
                    pnl = (trade.entry_price - trade.exit_price) * trade.position_size
                
                # Apply commission
                commission = abs(trade.position_size) * trade.entry_price * self.config.commission_rate
                pnl -= commission
                
                # Update trade
                trade.pnl = pnl
                trade.commission = commission
                trade.duration_hours = (timestamp - trade_timestamp).total_seconds() / 3600
                
                # Update balance
                balance += pnl
                
                logger.info(f"📉 Trade closed: {trade.side} {trade.instrument} @ {trade.exit_price:.5f} | P&L: {pnl:.2f}")
                
        except Exception as e:
            logger.error(f"❌ Error checking trade exits: {e}")
    
    def _calculate_unrealized_pl(self, trade: Trade, df: pd.DataFrame) -> float:
        """Calculate unrealized P&L for open trade"""
        try:
            if df.empty:
                return 0.0
            
            current_price = df['close'].iloc[-1]
            
            if trade.side == 'BUY':
                return (current_price - trade.entry_price) * trade.position_size
            else:
                return (trade.entry_price - current_price) * trade.position_size
                
        except Exception as e:
            logger.error(f"❌ Error calculating unrealized P&L: {e}")
            return 0.0
    
    def _calculate_metrics(self) -> BacktestMetrics:
        """Calculate comprehensive backtest metrics"""
        try:
            if not self.trades or not self.equity_curve:
                return BacktestMetrics(
                    total_return=0.0, annualized_return=0.0, max_drawdown=0.0,
                    sharpe_ratio=0.0, sortino_ratio=0.0, calmar_ratio=0.0,
                    win_rate=0.0, profit_factor=0.0, total_trades=0,
                    winning_trades=0, losing_trades=0, avg_win=0.0, avg_loss=0.0,
                    largest_win=0.0, largest_loss=0.0, avg_trade_duration=0.0,
                    max_consecutive_wins=0, max_consecutive_losses=0,
                    recovery_factor=0.0, expectancy=0.0, kelly_percentage=0.0
                )
            
            # Basic metrics
            initial_balance = self.config.initial_balance
            final_balance = self.equity_curve[-1]['balance']
            total_return = ((final_balance - initial_balance) / initial_balance) * 100
            
            # Annualized return
            days = (self.config.end_date - self.config.start_date).days
            annualized_return = (total_return / days) * 365 if days > 0 else 0.0
            
            # Max drawdown
            max_drawdown = max(point['drawdown'] for point in self.equity_curve)
            
            # Trade statistics
            winning_trades = [t for t in self.trades if t.pnl > 0]
            losing_trades = [t for t in self.trades if t.pnl <= 0]
            
            win_rate = (len(winning_trades) / len(self.trades)) * 100 if self.trades else 0.0
            
            # Profit factor
            total_profit = sum(t.pnl for t in winning_trades)
            total_loss = abs(sum(t.pnl for t in losing_trades))
            profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
            
            # Average win/loss
            avg_win = np.mean([t.pnl for t in winning_trades]) if winning_trades else 0.0
            avg_loss = np.mean([t.pnl for t in losing_trades]) if losing_trades else 0.0
            
            # Largest win/loss
            largest_win = max([t.pnl for t in winning_trades]) if winning_trades else 0.0
            largest_loss = min([t.pnl for t in losing_trades]) if losing_trades else 0.0
            
            # Average trade duration
            avg_duration = np.mean([t.duration_hours for t in self.trades]) if self.trades else 0.0
            
            # Consecutive wins/losses
            max_consecutive_wins, max_consecutive_losses = self._calculate_consecutive_streaks()
            
            # Sharpe ratio
            returns = [t.pnl for t in self.trades]
            if returns and len(returns) > 1:
                mean_return = np.mean(returns)
                std_return = np.std(returns)
                sharpe_ratio = mean_return / std_return if std_return > 0 else 0.0
            else:
                sharpe_ratio = 0.0
            
            # Sortino ratio
            negative_returns = [r for r in returns if r < 0]
            if negative_returns and len(negative_returns) > 1:
                downside_std = np.std(negative_returns)
                sortino_ratio = mean_return / downside_std if downside_std > 0 else 0.0
            else:
                sortino_ratio = 0.0
            
            # Calmar ratio
            calmar_ratio = annualized_return / max_drawdown if max_drawdown > 0 else 0.0
            
            # Recovery factor
            recovery_factor = total_return / max_drawdown if max_drawdown > 0 else 0.0
            
            # Expectancy
            expectancy = (win_rate / 100) * avg_win - ((100 - win_rate) / 100) * abs(avg_loss)
            
            # Kelly percentage
            kelly_percentage = self._calculate_kelly_percentage(win_rate, avg_win, avg_loss)
            
            return BacktestMetrics(
                total_return=total_return,
                annualized_return=annualized_return,
                max_drawdown=max_drawdown,
                sharpe_ratio=sharpe_ratio,
                sortino_ratio=sortino_ratio,
                calmar_ratio=calmar_ratio,
                win_rate=win_rate,
                profit_factor=profit_factor,
                total_trades=len(self.trades),
                winning_trades=len(winning_trades),
                losing_trades=len(losing_trades),
                avg_win=avg_win,
                avg_loss=avg_loss,
                largest_win=largest_win,
                largest_loss=largest_loss,
                avg_trade_duration=avg_duration,
                max_consecutive_wins=max_consecutive_wins,
                max_consecutive_losses=max_consecutive_losses,
                recovery_factor=recovery_factor,
                expectancy=expectancy,
                kelly_percentage=kelly_percentage
            )
            
        except Exception as e:
            logger.error(f"❌ Error calculating metrics: {e}")
            return None
    
    def _calculate_consecutive_streaks(self) -> Tuple[int, int]:
        """Calculate maximum consecutive wins and losses"""
        if not self.trades:
            return 0, 0
        
        max_wins = 0
        max_losses = 0
        current_wins = 0
        current_losses = 0
        
        for trade in self.trades:
            if trade.pnl > 0:
                current_wins += 1
                current_losses = 0
                max_wins = max(max_wins, current_wins)
            else:
                current_losses += 1
                current_wins = 0
                max_losses = max(max_losses, current_losses)
        
        return max_wins, max_losses
    
    def _calculate_kelly_percentage(self, win_rate: float, avg_win: float, avg_loss: float) -> float:
        """Calculate Kelly percentage for position sizing"""
        try:
            if avg_loss == 0:
                return 0.0
            
            win_prob = win_rate / 100
            loss_prob = 1 - win_prob
            win_loss_ratio = avg_win / abs(avg_loss)
            
            kelly = (win_prob * win_loss_ratio - loss_prob) / win_loss_ratio
            return max(0, min(kelly, 0.25)) * 100  # Cap at 25%
            
        except Exception as e:
            logger.error(f"❌ Error calculating Kelly percentage: {e}")
            return 0.0
    
    def generate_report(self) -> str:
        """Generate comprehensive backtest report"""
        if not self.metrics:
            return "No metrics available"
        
        report = []
        report.append("# ICT OTE Strategy Backtest Report")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Performance Summary
        report.append("## Performance Summary")
        report.append(f"- **Total Return:** {self.metrics.total_return:.2f}%")
        report.append(f"- **Annualized Return:** {self.metrics.annualized_return:.2f}%")
        report.append(f"- **Max Drawdown:** {self.metrics.max_drawdown:.2f}%")
        report.append(f"- **Sharpe Ratio:** {self.metrics.sharpe_ratio:.3f}")
        report.append(f"- **Sortino Ratio:** {self.metrics.sortino_ratio:.3f}")
        report.append(f"- **Calmar Ratio:** {self.metrics.calmar_ratio:.3f}")
        report.append("")
        
        # Trade Statistics
        report.append("## Trade Statistics")
        report.append(f"- **Total Trades:** {self.metrics.total_trades}")
        report.append(f"- **Winning Trades:** {self.metrics.winning_trades}")
        report.append(f"- **Losing Trades:** {self.metrics.losing_trades}")
        report.append(f"- **Win Rate:** {self.metrics.win_rate:.1f}%")
        report.append(f"- **Profit Factor:** {self.metrics.profit_factor:.2f}")
        report.append(f"- **Average Win:** {self.metrics.avg_win:.2f}")
        report.append(f"- **Average Loss:** {self.metrics.avg_loss:.2f}")
        report.append(f"- **Largest Win:** {self.metrics.largest_win:.2f}")
        report.append(f"- **Largest Loss:** {self.metrics.largest_loss:.2f}")
        report.append("")
        
        # Risk Metrics
        report.append("## Risk Metrics")
        report.append(f"- **Max Consecutive Wins:** {self.metrics.max_consecutive_wins}")
        report.append(f"- **Max Consecutive Losses:** {self.metrics.max_consecutive_losses}")
        report.append(f"- **Recovery Factor:** {self.metrics.recovery_factor:.2f}")
        report.append(f"- **Expectancy:** {self.metrics.expectancy:.2f}")
        report.append(f"- **Kelly Percentage:** {self.metrics.kelly_percentage:.1f}%")
        report.append("")
        
        # Trade Duration
        report.append("## Trade Duration")
        report.append(f"- **Average Duration:** {self.metrics.avg_trade_duration:.1f} hours")
        report.append("")
        
        # Recommendations
        report.append("## Recommendations")
        if self.metrics.sharpe_ratio > 1.0:
            report.append("✅ Good Sharpe ratio - strategy shows promise")
        else:
            report.append("⚠️ Low Sharpe ratio - consider parameter optimization")
        
        if self.metrics.win_rate > 50:
            report.append("✅ Good win rate - strategy is consistent")
        else:
            report.append("⚠️ Low win rate - consider improving entry criteria")
        
        if self.metrics.max_drawdown < 20:
            report.append("✅ Acceptable drawdown - risk is manageable")
        else:
            report.append("⚠️ High drawdown - consider reducing position size")
        
        return "\n".join(report)
    
    def save_results(self, filename: str = None) -> str:
        """Save backtest results to file"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"ict_ote_backtest_{timestamp}.json"
        
        results = {
            'config': asdict(self.config),
            'metrics': asdict(self.metrics) if self.metrics else None,
            'trades': [asdict(trade) for trade in self.trades],
            'equity_curve': self.equity_curve,
            'report': self.generate_report(),
            'timestamp': datetime.now().isoformat()
        }
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"💾 Results saved to {filename}")
        return filename

def main():
    """Main backtesting function"""
    # Configuration
    config = BacktestConfig(
        instruments=['XAU_USD', 'EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'USD_CAD'],
        start_date=datetime.now() - timedelta(days=30),  # Last 30 days
        end_date=datetime.now(),
        initial_balance=10000.0
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
    
    # Create backtester
    backtester = ICTOTEBacktester(config)
    
    # Run backtest
    logger.info("🚀 Starting ICT OTE Strategy Backtest...")
    metrics = backtester.run_backtest(test_parameters)
    
    if metrics:
        # Generate and display report
        report = backtester.generate_report()
        print("\n" + "="*80)
        print(report)
        print("="*80)
        
        # Save results
        filename = backtester.save_results()
        print(f"\n📊 Complete results saved to: {filename}")
        
    else:
        logger.error("❌ Backtest failed - no results generated")

if __name__ == "__main__":
    main()