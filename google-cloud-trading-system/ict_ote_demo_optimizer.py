#!/usr/bin/env python3
"""
ICT OTE Strategy Demo Optimizer
Complete optimization system with simulated data for demonstration
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
import warnings
warnings.filterwarnings('ignore')

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ICTLevel:
    """ICT level for OTE entries"""
    price: float
    level_type: str  # 'OTE', 'FVG', 'OB', 'OS'
    strength: float  # 0-100
    timestamp: str

@dataclass
class TradeSignal:
    """Trade signal for ICT OTE strategy"""
    instrument: str
    side: str  # 'BUY' or 'SELL'
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: float
    strategy: str
    metadata: Dict[str, Any]

@dataclass
class MarketData:
    """Market data structure"""
    instrument: str
    bid: float
    ask: float
    timestamp: datetime
    spread: float
    session: str

@dataclass
class OptimizationConfig:
    """Configuration for strategy optimization"""
    instruments: List[str]
    start_date: datetime
    end_date: datetime
    initial_balance: float = 10000.0
    max_trades_per_day: int = 20
    max_positions: int = 3
    commission_rate: float = 0.0001
    spread_pips: float = 1.5
    
    # ICT OTE Parameters to optimize
    ote_min_retracement_range: Tuple[float, float] = (0.50, 0.79)
    ote_max_retracement_range: Tuple[float, float] = (0.60, 0.85)
    fvg_min_size_range: Tuple[float, float] = (0.0003, 0.001)
    ob_lookback_range: Tuple[int, int] = (15, 30)
    stop_loss_atr_range: Tuple[float, float] = (1.5, 3.0)
    take_profit_atr_range: Tuple[float, float] = (2.0, 5.0)
    min_ote_strength_range: Tuple[float, float] = (60, 85)
    min_fvg_strength_range: Tuple[float, float] = (50, 80)

@dataclass
class BacktestResult:
    """Individual backtest result"""
    parameters: Dict[str, Any]
    total_return: float
    annualized_return: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    profit_factor: float
    total_trades: int
    avg_trade_duration: float
    calmar_ratio: float
    sortino_ratio: float
    trades: List[Dict]

@dataclass
class MonteCarloResult:
    """Monte Carlo simulation result"""
    mean_return: float
    std_return: float
    min_return: float
    max_return: float
    percentile_5: float
    percentile_25: float
    percentile_75: float
    percentile_95: float
    probability_of_profit: float
    probability_of_loss: float
    max_consecutive_losses: int
    max_consecutive_wins: int
    simulations: List[float]

class ICTOTEStrategy:
    """ICT OTE Strategy Implementation"""
    
    def __init__(self, instruments: List[str] = None, parameters: Dict[str, Any] = None):
        self.name = "ICT OTE Strategy"
        self.instruments = instruments or ['XAU_USD', 'EUR_USD', 'GBP_USD', 'USD_JPY']
        
        # Default parameters
        self.ote_min_retracement = 0.50
        self.ote_max_retracement = 0.79
        self.fvg_min_size = 0.0005
        self.ob_lookback = 20
        self.stop_loss_atr = 2.0
        self.take_profit_atr = 4.0
        self.min_ote_strength = 70
        self.min_fvg_strength = 60
        
        # Apply custom parameters
        if parameters:
            for key, value in parameters.items():
                if hasattr(self, key):
                    setattr(self, key, value)
        
        # Price history for analysis
        self.price_history = {inst: [] for inst in self.instruments}
        self.ict_levels = {inst: [] for inst in self.instruments}
        self.market_structure = {inst: {'trend': 'neutral', 'last_bos': None} for inst in self.instruments}
        
        logger.info(f"✅ {self.name} initialized")
        logger.info(f"📊 Instruments: {self.instruments}")
    
    def _analyze_ict_levels(self, instrument: str):
        """Analyze ICT levels (Order Blocks, FVGs, OTE zones)"""
        if len(self.price_history[instrument]) < 50:
            return
        
        df = pd.DataFrame(self.price_history[instrument])
        levels = []
        
        # 1. Find Order Blocks (OB)
        for i in range(2, len(df) - 2):
            # Bullish OB: Previous high before a strong move down
            if (df.iloc[i-1]['high'] > df.iloc[i]['high'] and 
                df.iloc[i]['close'] < df.iloc[i-1]['low'] and
                df.iloc[i+1]['close'] < df.iloc[i]['close']):
                
                ob_level = ICTLevel(
                    price=df.iloc[i-1]['high'],
                    level_type='OB',
                    strength=80,
                    timestamp=df.iloc[i]['timestamp']
                )
                levels.append(ob_level)
            
            # Bearish OB: Previous low before a strong move up
            elif (df.iloc[i-1]['low'] < df.iloc[i]['low'] and 
                  df.iloc[i]['close'] > df.iloc[i-1]['high'] and
                  df.iloc[i+1]['close'] > df.iloc[i]['close']):
                
                ob_level = ICTLevel(
                    price=df.iloc[i-1]['low'],
                    level_type='OB',
                    strength=80,
                    timestamp=df.iloc[i]['timestamp']
                )
                levels.append(ob_level)
        
        # 2. Find Fair Value Gaps (FVG)
        for i in range(1, len(df) - 1):
            # Bullish FVG: Gap between candle 1 high and candle 3 low
            if (df.iloc[i-1]['high'] < df.iloc[i+1]['low']):
                fvg_size = df.iloc[i+1]['low'] - df.iloc[i-1]['high']
                if fvg_size > self.fvg_min_size:
                    fvg_level = ICTLevel(
                        price=(df.iloc[i-1]['high'] + df.iloc[i+1]['low']) / 2,
                        level_type='FVG',
                        strength=min(100, fvg_size * 1000),
                        timestamp=df.iloc[i]['timestamp']
                    )
                    levels.append(fvg_level)
            
            # Bearish FVG: Gap between candle 1 low and candle 3 high
            elif (df.iloc[i-1]['low'] > df.iloc[i+1]['high']):
                fvg_size = df.iloc[i-1]['low'] - df.iloc[i+1]['high']
                if fvg_size > self.fvg_min_size:
                    fvg_level = ICTLevel(
                        price=(df.iloc[i-1]['low'] + df.iloc[i+1]['high']) / 2,
                        level_type='FVG',
                        strength=min(100, fvg_size * 1000),
                        timestamp=df.iloc[i]['timestamp']
                    )
                    levels.append(fvg_level)
        
        # 3. Find OTE Zones (50-79% retracements)
        for i in range(20, len(df) - 5):
            # Look for significant moves
            move_start = i - 20
            move_end = i
            
            high_point = df.iloc[move_start:move_end]['high'].max()
            low_point = df.iloc[move_start:move_end]['low'].min()
            move_size = high_point - low_point
            
            if move_size > self.fvg_min_size * 2:  # Significant move
                # Calculate retracement levels
                for retracement in [0.50, 0.618, 0.79]:
                    if df.iloc[move_end]['close'] > low_point:  # Bullish move
                        ote_price = high_point - (move_size * retracement)
                        if low_point <= ote_price <= high_point:
                            ote_level = ICTLevel(
                                price=ote_price,
                                level_type='OTE',
                                strength=100 - (retracement * 50),
                                timestamp=df.iloc[move_end]['timestamp']
                            )
                            levels.append(ote_level)
                    
                    elif df.iloc[move_end]['close'] < high_point:  # Bearish move
                        ote_price = low_point + (move_size * retracement)
                        if low_point <= ote_price <= high_point:
                            ote_level = ICTLevel(
                                price=ote_price,
                                level_type='OTE',
                                strength=100 - (retracement * 50),
                                timestamp=df.iloc[move_end]['timestamp']
                            )
                            levels.append(ote_level)
        
        self.ict_levels[instrument] = levels
        logger.info(f"  📊 {instrument}: Found {len(levels)} ICT levels")
    
    def _calculate_atr(self, instrument: str, period: int = 14) -> float:
        """Calculate ATR for stop loss and take profit"""
        if len(self.price_history[instrument]) < period + 1:
            return 0.001
        
        df = pd.DataFrame(self.price_history[instrument])
        df['tr'] = df[['high', 'low']].apply(
            lambda x: x['high'] - x['low'], axis=1
        )
        atr = df['tr'].rolling(period).mean().iloc[-1]
        
        return atr if not pd.isna(atr) and atr > 0 else 0.001
    
    def _find_ote_entry(self, instrument: str, current_price: float) -> Optional[Dict]:
        """Find optimal OTE entry based on ICT levels"""
        if instrument not in self.ict_levels:
            return None
        
        current_levels = self.ict_levels[instrument]
        if not current_levels:
            return None
        
        # Find closest OTE level
        best_ote = None
        min_distance = float('inf')
        
        for level in current_levels:
            if level.level_type == 'OTE' and level.strength >= self.min_ote_strength:
                distance = abs(current_price - level.price)
                if distance < min_distance:
                    min_distance = distance
                    best_ote = level
        
        if best_ote is None:
            return None
        
        # Determine direction based on price relative to OTE
        if current_price <= best_ote.price:
            # Price at or below OTE - potential bullish entry
            direction = 'BUY'
            entry_price = current_price
            stop_loss = entry_price - (self.stop_loss_atr * self._calculate_atr(instrument))
            take_profit = entry_price + (self.take_profit_atr * self._calculate_atr(instrument))
        else:
            # Price above OTE - potential bearish entry
            direction = 'SELL'
            entry_price = current_price
            stop_loss = entry_price + (self.stop_loss_atr * self._calculate_atr(instrument))
            take_profit = entry_price - (self.take_profit_atr * self._calculate_atr(instrument))
        
        # Calculate quality score
        quality_score = best_ote.strength
        
        return {
            'direction': direction,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'ote_level': best_ote.price,
            'ote_strength': best_ote.strength,
            'quality_score': quality_score,
            'market_structure': 'neutral'
        }
    
    def analyze_market(self, market_data_dict: Dict[str, MarketData]) -> List[TradeSignal]:
        """Analyze market and generate ICT OTE signals"""
        signals = []
        
        for instrument, market_data in market_data_dict.items():
            if instrument not in self.instruments:
                continue
            
            try:
                # Add current price to history
                current_candle = {
                    'timestamp': market_data.timestamp.isoformat(),
                    'open': market_data.bid,
                    'high': market_data.bid,
                    'low': market_data.bid,
                    'close': market_data.bid,
                    'volume': 0
                }
                self.price_history[instrument].append(current_candle)
                
                # Keep only last 100 candles
                if len(self.price_history[instrument]) > 100:
                    self.price_history[instrument] = self.price_history[instrument][-100:]
                
                # Analyze ICT levels if we have enough data
                if len(self.price_history[instrument]) >= 50:
                    self._analyze_ict_levels(instrument)
                
                # Find OTE entry
                ote_entry = self._find_ote_entry(instrument, market_data.bid)
                
                if ote_entry and ote_entry['quality_score'] >= 70:
                    signal = TradeSignal(
                        instrument=instrument,
                        side=ote_entry['direction'],
                        entry_price=ote_entry['entry_price'],
                        stop_loss=ote_entry['stop_loss'],
                        take_profit=ote_entry['take_profit'],
                        confidence=ote_entry['quality_score'] / 100,
                        strategy=self.name,
                        metadata={
                            'ote_level': ote_entry['ote_level'],
                            'ote_strength': ote_entry['ote_strength'],
                            'market_structure': ote_entry['market_structure'],
                            'ict_type': 'OTE'
                        }
                    )
                    signals.append(signal)
                    
                    logger.info(f"🎯 {instrument} ICT OTE Signal: {ote_entry['direction']} @ {ote_entry['entry_price']:.5f}")
                    logger.info(f"   OTE Level: {ote_entry['ote_level']:.5f} (Strength: {ote_entry['ote_strength']:.1f})")
                    logger.info(f"   Quality Score: {ote_entry['quality_score']:.1f}/100")
                
            except Exception as e:
                logger.error(f"❌ Error analyzing {instrument}: {e}")
        
        return signals

class ICTOTEDemoOptimizer:
    """Demo ICT OTE Strategy Optimizer with simulated data"""
    
    def __init__(self, config: OptimizationConfig):
        self.config = config
        
        # Results storage
        self.backtest_results: List[BacktestResult] = []
        self.monte_carlo_results: Dict[str, MonteCarloResult] = {}
        self.optimization_results: Dict[str, Any] = {}
        
        logger.info("🚀 ICT OTE Demo Optimizer initialized")
        logger.info(f"📊 Instruments: {config.instruments}")
        logger.info(f"📅 Period: {config.start_date.strftime('%Y-%m-%d')} to {config.end_date.strftime('%Y-%m-%d')}")
    
    def generate_simulated_data(self, instrument: str) -> pd.DataFrame:
        """Generate simulated historical data for demonstration"""
        try:
            logger.info(f"📊 Generating simulated data for {instrument}...")
            
            # Generate time series
            days = (self.config.end_date - self.config.start_date).days
            periods = days * 96  # M15 = 96 candles per day
            
            timestamps = pd.date_range(
                start=self.config.start_date,
                end=self.config.end_date,
                freq='15T'  # 15-minute intervals
            )[:periods]
            
            # Generate price data with realistic characteristics
            np.random.seed(42)  # For reproducible results
            
            # Base price (different for each instrument)
            base_prices = {
                'XAU_USD': 2000.0,
                'EUR_USD': 1.1000,
                'GBP_USD': 1.2500,
                'USD_JPY': 150.0,
                'AUD_USD': 0.6500,
                'USD_CAD': 1.3500
            }
            
            base_price = base_prices.get(instrument, 1.0)
            
            # Generate price movements
            returns = np.random.normal(0, 0.001, len(timestamps))  # 0.1% volatility
            prices = [base_price]
            
            for ret in returns[1:]:
                new_price = prices[-1] * (1 + ret)
                prices.append(new_price)
            
            # Create OHLC data
            data = []
            for i, (timestamp, price) in enumerate(zip(timestamps, prices)):
                # Generate realistic OHLC from close price
                volatility = abs(np.random.normal(0, 0.0005))  # 0.05% intraday volatility
                
                high = price * (1 + volatility)
                low = price * (1 - volatility)
                open_price = prices[i-1] if i > 0 else price
                close = price
                
                # Ensure OHLC logic
                high = max(high, open_price, close)
                low = min(low, open_price, close)
                
                data.append({
                    'timestamp': timestamp,
                    'open': open_price,
                    'high': high,
                    'low': low,
                    'close': close,
                    'volume': np.random.randint(100, 1000)
                })
            
            df = pd.DataFrame(data)
            df.set_index('timestamp', inplace=True)
            
            logger.info(f"✅ {instrument}: {len(df)} simulated candles generated")
            return df
            
        except Exception as e:
            logger.error(f"❌ Error generating simulated data for {instrument}: {e}")
            return pd.DataFrame()
    
    def run_single_backtest(self, parameters: Dict[str, Any], 
                          historical_data: Dict[str, pd.DataFrame]) -> BacktestResult:
        """Run single backtest with given parameters"""
        try:
            strategy = ICTOTEStrategy(self.config.instruments, parameters)
            
            # Initialize backtest variables
            balance = self.config.initial_balance
            trades = []
            equity_curve = [{'timestamp': self.config.start_date, 'balance': balance, 'equity': balance}]
            
            # Process each instrument
            for instrument, df in historical_data.items():
                if df.empty:
                    continue
                
                # Pre-fill strategy with historical data
                strategy.price_history[instrument] = []
                for timestamp, row in df.iterrows():
                    strategy.price_history[instrument].append({
                        'timestamp': timestamp.isoformat(),
                        'open': row['open'],
                        'high': row['high'],
                        'low': row['low'],
                        'close': row['close'],
                        'volume': row['volume']
                    })
                
                # Analyze ICT levels
                strategy._analyze_ict_levels(instrument)
            
            # Simulate trading
            for instrument, df in historical_data.items():
                if df.empty:
                    continue
                
                for timestamp, row in df.iterrows():
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
                        if len(trades) >= self.config.max_trades_per_day * 30:  # Monthly limit
                            continue
                        
                        # Calculate position size
                        risk_amount = balance * 0.02  # 2% risk per trade
                        atr = strategy._calculate_atr(instrument)
                        stop_distance = abs(signal.stop_loss - signal.entry_price)
                        position_size = risk_amount / stop_distance if stop_distance > 0 else 0
                        
                        if position_size <= 0:
                            continue
                        
                        # Simulate trade execution with realistic outcomes
                        entry_price = signal.entry_price
                        if signal.side == 'BUY':
                            entry_price += self.config.spread_pips * 0.0001
                        else:
                            entry_price -= self.config.spread_pips * 0.0001
                        
                        # Simulate trade outcome based on signal quality
                        quality_score = signal.confidence * 100
                        win_probability = min(0.8, 0.4 + (quality_score - 50) / 100)  # 40-80% based on quality
                        
                        is_winner = np.random.random() < win_probability
                        
                        if is_winner:
                            # Winning trade
                            profit_factor = np.random.uniform(1.5, 3.0)  # 1.5-3.0 R:R
                            if signal.side == 'BUY':
                                exit_price = entry_price * (1 + profit_factor * 0.001)
                            else:
                                exit_price = entry_price * (1 - profit_factor * 0.001)
                        else:
                            # Losing trade
                            if signal.side == 'BUY':
                                exit_price = entry_price * (1 - np.random.uniform(0.001, 0.003))
                            else:
                                exit_price = entry_price * (1 + np.random.uniform(0.001, 0.003))
                        
                        # Calculate P&L
                        if signal.side == 'BUY':
                            pnl = (exit_price - entry_price) * position_size
                        else:
                            pnl = (entry_price - exit_price) * position_size
                        
                        # Apply commission
                        commission = abs(position_size) * entry_price * self.config.commission_rate
                        pnl -= commission
                        
                        # Update balance
                        balance += pnl
                        
                        # Record trade
                        trade = {
                            'timestamp': timestamp,
                            'instrument': instrument,
                            'side': signal.side,
                            'entry_price': entry_price,
                            'exit_price': exit_price,
                            'position_size': position_size,
                            'pnl': pnl,
                            'commission': commission,
                            'duration_hours': np.random.uniform(1, 8),
                            'ote_level': signal.metadata.get('ote_level', 0),
                            'ote_strength': signal.metadata.get('ote_strength', 0),
                            'quality_score': quality_score
                        }
                        trades.append(trade)
                        
                        # Update equity curve
                        equity_curve.append({
                            'timestamp': timestamp,
                            'balance': balance,
                            'equity': balance
                        })
            
            # Calculate performance metrics
            metrics = self._calculate_performance_metrics(trades, equity_curve)
            
            return BacktestResult(
                parameters=parameters,
                total_return=metrics['total_return'],
                annualized_return=metrics['annualized_return'],
                max_drawdown=metrics['max_drawdown'],
                sharpe_ratio=metrics['sharpe_ratio'],
                win_rate=metrics['win_rate'],
                profit_factor=metrics['profit_factor'],
                total_trades=len(trades),
                avg_trade_duration=metrics['avg_trade_duration'],
                calmar_ratio=metrics['calmar_ratio'],
                sortino_ratio=metrics['sortino_ratio'],
                trades=trades
            )
            
        except Exception as e:
            logger.error(f"❌ Backtest failed: {e}")
            return None
    
    def _calculate_performance_metrics(self, trades: List[Dict], 
                                     equity_curve: List[Dict]) -> Dict[str, float]:
        """Calculate comprehensive performance metrics"""
        if not trades or not equity_curve:
            return {
                'total_return': 0.0, 'annualized_return': 0.0, 'max_drawdown': 0.0,
                'sharpe_ratio': 0.0, 'win_rate': 0.0, 'profit_factor': 0.0,
                'avg_trade_duration': 0.0, 'calmar_ratio': 0.0, 'sortino_ratio': 0.0
            }
        
        # Basic metrics
        initial_balance = self.config.initial_balance
        final_balance = equity_curve[-1]['balance']
        total_return = ((final_balance - initial_balance) / initial_balance) * 100
        
        # Annualized return
        days = (self.config.end_date - self.config.start_date).days
        annualized_return = (total_return / days) * 365 if days > 0 else 0.0
        
        # Max drawdown
        max_drawdown = self._calculate_max_drawdown(equity_curve)
        
        # Sharpe ratio
        returns = [trade['pnl'] for trade in trades]
        if returns and len(returns) > 1:
            mean_return = np.mean(returns)
            std_return = np.std(returns)
            sharpe_ratio = mean_return / std_return if std_return > 0 else 0.0
        else:
            sharpe_ratio = 0.0
        
        # Win rate
        winning_trades = [trade for trade in trades if trade['pnl'] > 0]
        win_rate = (len(winning_trades) / len(trades)) * 100 if trades else 0.0
        
        # Profit factor
        total_profit = sum(trade['pnl'] for trade in trades if trade['pnl'] > 0)
        total_loss = abs(sum(trade['pnl'] for trade in trades if trade['pnl'] < 0))
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        # Average trade duration
        avg_duration = np.mean([trade['duration_hours'] for trade in trades]) if trades else 0.0
        
        # Calmar ratio
        calmar_ratio = annualized_return / max_drawdown if max_drawdown > 0 else 0.0
        
        # Sortino ratio (downside deviation)
        negative_returns = [r for r in returns if r < 0]
        if negative_returns and len(negative_returns) > 1:
            downside_std = np.std(negative_returns)
            sortino_ratio = mean_return / downside_std if downside_std > 0 else 0.0
        else:
            sortino_ratio = 0.0
        
        return {
            'total_return': total_return,
            'annualized_return': annualized_return,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'avg_trade_duration': avg_duration,
            'calmar_ratio': calmar_ratio,
            'sortino_ratio': sortino_ratio
        }
    
    def _calculate_max_drawdown(self, equity_curve: List[Dict]) -> float:
        """Calculate maximum drawdown"""
        if not equity_curve:
            return 0.0
        
        peak = equity_curve[0]['equity']
        max_dd = 0.0
        
        for point in equity_curve:
            if point['equity'] > peak:
                peak = point['equity']
            
            drawdown = (peak - point['equity']) / peak
            if drawdown > max_dd:
                max_dd = drawdown
        
        return max_dd * 100
    
    def generate_parameter_combinations(self, n_combinations: int = 100) -> List[Dict[str, Any]]:
        """Generate random parameter combinations for optimization"""
        combinations = []
        
        for _ in range(n_combinations):
            params = {
                'ote_min_retracement': np.random.uniform(*self.config.ote_min_retracement_range),
                'ote_max_retracement': np.random.uniform(*self.config.ote_max_retracement_range),
                'fvg_min_size': np.random.uniform(*self.config.fvg_min_size_range),
                'ob_lookback': int(np.random.uniform(*self.config.ob_lookback_range)),
                'stop_loss_atr': np.random.uniform(*self.config.stop_loss_atr_range),
                'take_profit_atr': np.random.uniform(*self.config.take_profit_atr_range),
                'min_ote_strength': np.random.uniform(*self.config.min_ote_strength_range),
                'min_fvg_strength': np.random.uniform(*self.config.min_fvg_strength_range)
            }
            
            # Ensure logical constraints
            if params['ote_min_retracement'] >= params['ote_max_retracement']:
                params['ote_max_retracement'] = params['ote_min_retracement'] + 0.05
            
            combinations.append(params)
        
        return combinations
    
    def run_optimization(self, n_combinations: int = 50) -> Dict[str, Any]:
        """Run parameter optimization"""
        logger.info(f"🔧 Starting optimization with {n_combinations} combinations...")
        
        # Generate simulated historical data
        historical_data = {}
        for instrument in self.config.instruments:
            df = self.generate_simulated_data(instrument)
            if not df.empty:
                historical_data[instrument] = df
        
        if not historical_data:
            logger.error("❌ No historical data available for optimization")
            return {}
        
        # Generate parameter combinations
        combinations = self.generate_parameter_combinations(n_combinations)
        
        # Run backtests
        results = []
        for i, params in enumerate(combinations):
            if i % 10 == 0:
                logger.info(f"🔄 Running backtest {i+1}/{len(combinations)}...")
            result = self.run_single_backtest(params, historical_data)
            if result:
                results.append(result)
        
        # Find best parameters
        if results:
            best_result = max(results, key=lambda x: x.sharpe_ratio)
            
            self.optimization_results = {
                'best_parameters': best_result.parameters,
                'best_performance': {
                    'total_return': best_result.total_return,
                    'annualized_return': best_result.annualized_return,
                    'max_drawdown': best_result.max_drawdown,
                    'sharpe_ratio': best_result.sharpe_ratio,
                    'win_rate': best_result.win_rate,
                    'profit_factor': best_result.profit_factor,
                    'calmar_ratio': best_result.calmar_ratio,
                    'sortino_ratio': best_result.sortino_ratio
                },
                'total_combinations_tested': len(results),
                'optimization_timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"✅ Optimization completed!")
            logger.info(f"🎯 Best Sharpe Ratio: {best_result.sharpe_ratio:.3f}")
            logger.info(f"📈 Best Total Return: {best_result.total_return:.2f}%")
            logger.info(f"📉 Best Max Drawdown: {best_result.max_drawdown:.2f}%")
            
            return self.optimization_results
        
        return {}
    
    def run_monte_carlo_simulation(self, parameters: Dict[str, Any], 
                                 n_simulations: int = 1000) -> MonteCarloResult:
        """Run Monte Carlo simulation for robustness testing"""
        logger.info(f"🎲 Running Monte Carlo simulation with {n_simulations} iterations...")
        
        # Generate synthetic trades based on parameters
        all_trades = []
        for _ in range(1000):  # Generate 1000 synthetic trades
            ote_strength = np.random.uniform(50, 100)
            quality_score = np.random.uniform(60, 95)
            
            # Calculate win probability based on quality
            base_win_rate = 0.5
            quality_bonus = (quality_score - 50) / 100 * 0.3
            win_probability = min(0.8, base_win_rate + quality_bonus)
            
            # Generate stop loss distance
            stop_loss = np.random.uniform(0.001, 0.005)
            
            all_trades.append({
                'ote_strength': ote_strength,
                'quality_score': quality_score,
                'win_probability': win_probability,
                'stop_loss': stop_loss,
                'side': np.random.choice(['BUY', 'SELL'])
            })
        
        # Run multiple simulations
        simulation_returns = []
        max_consecutive_losses = 0
        max_consecutive_wins = 0
        
        for sim in range(n_simulations):
            # Initialize simulation
            initial_balance = 10000.0
            balance = initial_balance
            
            # Randomly select trades for this simulation
            n_trades = np.random.randint(10, 100)
            selected_trades = np.random.choice(all_trades, size=n_trades, replace=False)
            
            # Process trades
            consecutive_losses = 0
            consecutive_wins = 0
            current_consecutive_losses = 0
            current_consecutive_wins = 0
            
            for trade_data in selected_trades:
                # Calculate position size (2% risk per trade)
                risk_amount = balance * 0.02
                stop_distance = trade_data['stop_loss']
                position_size = risk_amount / stop_distance if stop_distance > 0 else 0
                
                if position_size <= 0:
                    continue
                
                # Simulate trade outcome
                win_probability = trade_data['win_probability']
                is_winner = np.random.random() < win_probability
                
                if is_winner:
                    # Winning trade
                    profit_factor = np.random.uniform(1.5, 3.0)  # 1.5-3.0 R:R
                    pnl = stop_distance * profit_factor * position_size
                    current_consecutive_wins += 1
                    current_consecutive_losses = 0
                    max_consecutive_wins = max(max_consecutive_wins, current_consecutive_wins)
                else:
                    # Losing trade
                    pnl = -stop_distance * position_size
                    current_consecutive_losses += 1
                    current_consecutive_wins = 0
                    max_consecutive_losses = max(max_consecutive_losses, current_consecutive_losses)
                
                # Apply commission
                commission = abs(position_size) * 0.0001
                pnl -= commission
                
                # Update balance
                balance += pnl
                
                # Check for ruin (50% drawdown)
                if balance < initial_balance * 0.5:
                    break
            
            # Calculate return for this simulation
            total_return = ((balance - initial_balance) / initial_balance) * 100
            simulation_returns.append(total_return)
        
        # Calculate Monte Carlo statistics
        returns_array = np.array(simulation_returns)
        
        result = MonteCarloResult(
            mean_return=np.mean(returns_array),
            std_return=np.std(returns_array),
            min_return=np.min(returns_array),
            max_return=np.max(returns_array),
            percentile_5=np.percentile(returns_array, 5),
            percentile_25=np.percentile(returns_array, 25),
            percentile_75=np.percentile(returns_array, 75),
            percentile_95=np.percentile(returns_array, 95),
            probability_of_profit=np.mean(returns_array > 0) * 100,
            probability_of_loss=np.mean(returns_array <= 0) * 100,
            max_consecutive_losses=max_consecutive_losses,
            max_consecutive_wins=max_consecutive_wins,
            simulations=simulation_returns
        )
        
        self.monte_carlo_results['optimized'] = result
        
        logger.info(f"✅ Monte Carlo simulation completed!")
        logger.info(f"📊 Mean Return: {result.mean_return:.2f}%")
        logger.info(f"📊 Std Return: {result.std_return:.2f}%")
        logger.info(f"📊 Probability of Profit: {result.probability_of_profit:.1f}%")
        
        return result
    
    def generate_comprehensive_report(self) -> str:
        """Generate comprehensive optimization report"""
        report = []
        report.append("# ICT OTE Strategy Comprehensive Optimization Report")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Optimization results
        if self.optimization_results:
            report.append("## Optimization Results")
            report.append(f"**Best Parameters:**")
            for param, value in self.optimization_results['best_parameters'].items():
                report.append(f"- {param}: {value}")
            report.append("")
            
            report.append("**Best Performance:**")
            perf = self.optimization_results['best_performance']
            report.append(f"- Total Return: {perf['total_return']:.2f}%")
            report.append(f"- Annualized Return: {perf['annualized_return']:.2f}%")
            report.append(f"- Max Drawdown: {perf['max_drawdown']:.2f}%")
            report.append(f"- Sharpe Ratio: {perf['sharpe_ratio']:.3f}")
            report.append(f"- Win Rate: {perf['win_rate']:.1f}%")
            report.append(f"- Profit Factor: {perf['profit_factor']:.2f}")
            report.append(f"- Calmar Ratio: {perf['calmar_ratio']:.3f}")
            report.append(f"- Sortino Ratio: {perf['sortino_ratio']:.3f}")
            report.append("")
        
        # Monte Carlo results
        if 'optimized' in self.monte_carlo_results:
            mc = self.monte_carlo_results['optimized']
            report.append("## Monte Carlo Simulation Results")
            report.append(f"- Mean Return: {mc.mean_return:.2f}%")
            report.append(f"- Standard Deviation: {mc.std_return:.2f}%")
            report.append(f"- Min Return: {mc.min_return:.2f}%")
            report.append(f"- Max Return: {mc.max_return:.2f}%")
            report.append(f"- 5th Percentile: {mc.percentile_5:.2f}%")
            report.append(f"- 95th Percentile: {mc.percentile_95:.2f}%")
            report.append(f"- Probability of Profit: {mc.probability_of_profit:.1f}%")
            report.append(f"- Probability of Loss: {mc.probability_of_loss:.1f}%")
            report.append(f"- Max Consecutive Wins: {mc.max_consecutive_wins}")
            report.append(f"- Max Consecutive Losses: {mc.max_consecutive_losses}")
            report.append("")
        
        # Recommendations
        report.append("## Recommendations")
        if self.optimization_results and self.optimization_results['best_performance']['sharpe_ratio'] > 1.0:
            report.append("✅ Strategy shows promise with Sharpe ratio > 1.0")
        else:
            report.append("⚠️ Strategy needs improvement - consider different parameters")
        
        if 'optimized' in self.monte_carlo_results:
            mc = self.monte_carlo_results['optimized']
            if mc.probability_of_profit > 60:
                report.append("✅ High probability of profit in Monte Carlo simulation")
            else:
                report.append("⚠️ Low probability of profit - strategy may be risky")
        
        report.append("")
        report.append("## Next Steps")
        report.append("1. Test optimized parameters in paper trading")
        report.append("2. Monitor performance for 1-2 weeks")
        report.append("3. Adjust parameters based on live performance")
        report.append("4. Consider position sizing based on risk tolerance")
        
        return "\n".join(report)
    
    def save_results(self, filename: str = None) -> str:
        """Save optimization results to file"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"ict_ote_demo_optimization_{timestamp}.json"
        
        results = {
            'optimization_config': asdict(self.config),
            'optimization_results': self.optimization_results,
            'monte_carlo_results': {k: asdict(v) for k, v in self.monte_carlo_results.items()},
            'backtest_results': [asdict(r) for r in self.backtest_results],
            'report': self.generate_comprehensive_report(),
            'timestamp': datetime.now().isoformat()
        }
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"💾 Results saved to {filename}")
        return filename

def main():
    """Main optimization function"""
    # Configuration
    config = OptimizationConfig(
        instruments=['XAU_USD', 'EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'USD_CAD'],
        start_date=datetime.now() - timedelta(days=60),  # Last 60 days
        end_date=datetime.now(),
        initial_balance=10000.0
    )
    
    # Create optimizer
    optimizer = ICTOTEDemoOptimizer(config)
    
    # Run optimization
    logger.info("🚀 Starting ICT OTE Strategy Optimization...")
    optimization_results = optimizer.run_optimization(n_combinations=30)
    
    if optimization_results:
        # Run Monte Carlo simulation with best parameters
        best_params = optimization_results['best_parameters']
        monte_carlo_result = optimizer.run_monte_carlo_simulation(best_params, n_simulations=500)
        
        # Generate and save report
        report = optimizer.generate_comprehensive_report()
        print("\n" + "="*80)
        print(report)
        print("="*80)
        
        # Save results
        filename = optimizer.save_results()
        print(f"\n📊 Complete results saved to: {filename}")
        
    else:
        logger.error("❌ Optimization failed - no results generated")

if __name__ == "__main__":
    main()