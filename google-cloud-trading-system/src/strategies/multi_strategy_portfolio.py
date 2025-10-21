#!/usr/bin/env python3
"""
Multi-Strategy Portfolio Manager
Manages all 4 optimized strategies as a unified portfolio
Based on MULTI_STRATEGY_PORTFOLIO.yaml configuration
"""

import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from src.core.order_manager import TradeSignal, OrderSide
from src.core.data_feed import MarketData

# Import individual strategies
from src.strategies.aud_usd_5m_high_return import get_aud_usd_high_return_strategy
from src.strategies.eur_usd_5m_safe import get_eur_usd_safe_strategy
from src.strategies.xau_usd_5m_gold_high_return import get_xau_usd_gold_high_return_strategy
try:
    from src.strategies.gbp_usd_optimized import get_strategy_rank_1  # Assuming GBP/USD exists
except ImportError:
    # Fallback if GBP/USD strategy doesn't exist
    get_strategy_rank_1 = None

logger = logging.getLogger(__name__)

@dataclass
class PortfolioPerformance:
    """Portfolio performance metrics"""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_return: float
    max_drawdown: float
    sharpe_ratio: float
    profit_factor: float

class MultiStrategyPortfolio:
    """Multi-Strategy Portfolio Manager - Manages 4 optimized strategies"""
    
    def __init__(self):
        self.name = "Multi_Strategy_Portfolio"
        self.description = "Portfolio of 4 optimized strategies for maximum diversification"
        
        # Initialize individual strategies
        self.strategies = {
            'AUD_USD_High_Return': get_aud_usd_high_return_strategy(),
            'EUR_USD_Safe': get_eur_usd_safe_strategy(),
            'XAU_USD_Gold_High_Return': get_xau_usd_gold_high_return_strategy(),
        }
        
        # Add GBP/USD strategy if available
        if get_strategy_rank_1:
            self.strategies['GBP_USD_Champion'] = get_strategy_rank_1()
        
        # Portfolio configuration from YAML
        self.portfolio_config = {
            'initial_capital': 20000,
            'base_currency': 'USD',
            'broker': 'OANDA',
            'account_type': 'DEMO',  # Start with DEMO
            
            'risk_management': {
                'risk_per_trade_pct': 1.5,
                'max_total_positions': 5,
                'max_positions_per_pair': 2,
                'max_daily_trades_per_pair': 100,
                'total_portfolio_risk_limit_pct': 10.0,
                'max_account_drawdown_pct': 15.0,
                'daily_loss_limit_pct': 5.0
            },
            
            'capital_allocation': {
                'GBP_USD': {'amount': 6000, 'percentage': 30, 'reason': 'Best Sharpe ratio'},
                'EUR_USD': {'amount': 6000, 'percentage': 30, 'reason': 'Safest, lowest drawdown'},
                'XAU_USD': {'amount': 4000, 'percentage': 20, 'reason': 'Highest returns'},
                'AUD_USD': {'amount': 4000, 'percentage': 20, 'reason': 'High growth, diversification'}
            },
            
            'trading_sessions': {
                'asian_session': {'enabled': True, 'start': '00:00', 'end': '08:00', 'pairs': ['AUD_USD']},
                'london_session': {'enabled': True, 'start': '08:00', 'end': '17:00', 'pairs': ['GBP_USD', 'EUR_USD', 'XAU_USD', 'AUD_USD']},
                'ny_session': {'enabled': True, 'start': '13:00', 'end': '20:00', 'pairs': ['GBP_USD', 'EUR_USD', 'XAU_USD', 'AUD_USD']},
                'late_ny_session': {'enabled': False, 'start': '20:00', 'end': '24:00', 'pairs': []}
            }
        }
        
        # Performance tracking
        self.portfolio_performance = PortfolioPerformance(
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0.0,
            total_return=0.0,
            max_drawdown=0.0,
            sharpe_ratio=0.0,
            profit_factor=0.0
        )
        
        # Daily tracking
        self.daily_trades = 0
        self.daily_pnl = 0.0
        self.last_reset_date = datetime.now().date()
        
        # All instruments across strategies
        self.all_instruments = []
        for strategy in self.strategies.values():
            if hasattr(strategy, 'instruments'):
                self.all_instruments.extend(strategy.instruments)
            elif hasattr(strategy, 'instrument'):
                self.all_instruments.append(strategy.instrument)
        self.all_instruments = list(set(self.all_instruments))  # Remove duplicates
        
        logger.info(f"✅ {self.name} initialized with {len(self.strategies)} strategies")
        logger.info(f"📊 Instruments: {', '.join(self.all_instruments)}")
        logger.info(f"💰 Initial capital: ${self.portfolio_config['initial_capital']:,}")
    
    def _reset_daily_counters(self):
        """Reset daily counters if new day"""
        current_date = datetime.now().date()
        if current_date != self.last_reset_date:
            self.daily_trades = 0
            self.daily_pnl = 0.0
            self.last_reset_date = current_date
    
    def _check_portfolio_risk_limits(self) -> Tuple[bool, str]:
        """Check portfolio-wide risk limits"""
        self._reset_daily_counters()
        
        # Check daily trade limit
        if self.daily_trades >= self.portfolio_config['risk_management']['max_total_positions'] * 10:  # Conservative multiplier
            return False, f"Portfolio daily trade limit reached: {self.daily_trades}"
        
        # Check daily loss limit
        if abs(self.daily_pnl) > self.portfolio_config['risk_management']['daily_loss_limit_pct'] / 100 * self.portfolio_config['initial_capital']:
            return False, f"Daily loss limit exceeded: ${abs(self.daily_pnl):.2f}"
        
        return True, "OK"
    
    def _get_current_trading_session(self) -> str:
        """Get current trading session"""
        now = datetime.now().time()
        
        sessions = self.portfolio_config['trading_sessions']
        
        # Asian session (00:00-08:00)
        if datetime.strptime('00:00', '%H:%M').time() <= now < datetime.strptime('08:00', '%H:%M').time():
            return 'asian_session'
        
        # London session (08:00-17:00)
        elif datetime.strptime('08:00', '%H:%M').time() <= now < datetime.strptime('17:00', '%H:%M').time():
            return 'london_session'
        
        # NY session (13:00-20:00)
        elif datetime.strptime('13:00', '%H:%M').time() <= now < datetime.strptime('20:00', '%H:%M').time():
            return 'ny_session'
        
        # Late NY session (20:00-24:00)
        elif datetime.strptime('20:00', '%H:%M').time() <= now:
            return 'late_ny_session'
        
        return 'asian_session'  # Default fallback
    
    def _filter_signals_by_session(self, signals: List[TradeSignal]) -> List[TradeSignal]:
        """Filter signals based on current trading session"""
        current_session = self._get_current_trading_session()
        session_config = self.portfolio_config['trading_sessions'][current_session]
        
        if not session_config['enabled']:
            logger.info(f"🚫 Session {current_session} is disabled - no signals")
            return []
        
        allowed_pairs = session_config['pairs']
        filtered_signals = []
        
        for signal in signals:
            # Extract pair from instrument (e.g., 'EUR_USD' from 'EUR_USD')
            pair = signal.instrument
            if pair in allowed_pairs:
                filtered_signals.append(signal)
            else:
                logger.info(f"🚫 Signal for {pair} filtered out - not allowed in {current_session}")
        
        return filtered_signals
    
    def _apply_portfolio_risk_management(self, signals: List[TradeSignal]) -> List[TradeSignal]:
        """Apply portfolio-level risk management"""
        if not signals:
            return signals
        
        # Sort signals by confidence (highest first)
        signals.sort(key=lambda x: x.confidence, reverse=True)
        
        # Limit total positions
        max_positions = self.portfolio_config['risk_management']['max_total_positions']
        if len(signals) > max_positions:
            signals = signals[:max_positions]
            logger.info(f"🔒 Limited to {max_positions} positions for portfolio risk management")
        
        # Limit positions per pair
        max_per_pair = self.portfolio_config['risk_management']['max_positions_per_pair']
        pair_counts = {}
        filtered_signals = []
        
        for signal in signals:
            pair = signal.instrument
            pair_counts[pair] = pair_counts.get(pair, 0) + 1
            
            if pair_counts[pair] <= max_per_pair:
                filtered_signals.append(signal)
            else:
                logger.info(f"🔒 Signal for {pair} filtered out - max {max_per_pair} per pair reached")
        
        return filtered_signals
    
    def analyze_market(self, market_data: Dict[str, MarketData]) -> List[TradeSignal]:
        """Analyze market using all strategies and return unified signals"""
        
        # Check portfolio risk limits
        can_trade, reason = self._check_portfolio_risk_limits()
        if not can_trade:
            logger.warning(f"⚠️ Portfolio risk limit: {reason}")
            return []
        
        all_signals = []
        
        # Get signals from each strategy
        for strategy_name, strategy in self.strategies.items():
            try:
                strategy_signals = strategy.analyze_market(market_data)
                
                # Add strategy name to signals
                for signal in strategy_signals:
                    signal.strategy_name = f"{strategy_name}_{signal.strategy_name}"
                
                all_signals.extend(strategy_signals)
                logger.info(f"📊 {strategy_name}: {len(strategy_signals)} signals")
                
            except Exception as e:
                logger.error(f"❌ Error in {strategy_name}: {e}")
        
        # Filter by trading session
        session_filtered_signals = self._filter_signals_by_session(all_signals)
        logger.info(f"🕐 Session filtered: {len(session_filtered_signals)} signals")
        
        # Apply portfolio risk management
        final_signals = self._apply_portfolio_risk_management(session_filtered_signals)
        logger.info(f"🔒 Risk managed: {len(final_signals)} final signals")
        
        # Update portfolio tracking
        self.daily_trades += len(final_signals)
        
        return final_signals
    
    def update_performance(self, trade_result: Dict):
        """Update portfolio performance metrics"""
        self.portfolio_performance.total_trades += 1
        
        if trade_result.get('pnl', 0) > 0:
            self.portfolio_performance.winning_trades += 1
        else:
            self.portfolio_performance.losing_trades += 1
        
        # Update daily PnL
        self.daily_pnl += trade_result.get('pnl', 0)
        
        # Recalculate metrics
        if self.portfolio_performance.total_trades > 0:
            self.portfolio_performance.win_rate = (
                self.portfolio_performance.winning_trades / 
                self.portfolio_performance.total_trades * 100
            )
        
        logger.info(f"📈 Portfolio performance updated: {self.portfolio_performance.win_rate:.1f}% win rate")
    
    def get_portfolio_info(self) -> Dict:
        """Get comprehensive portfolio information"""
        current_session = self._get_current_trading_session()
        session_config = self.portfolio_config['trading_sessions'][current_session]
        
        return {
            'name': self.name,
            'description': self.description,
            'strategies': {
                name: strategy.get_strategy_info() for name, strategy in self.strategies.items()
            },
            'portfolio_config': self.portfolio_config,
            'performance': {
                'total_trades': self.portfolio_performance.total_trades,
                'winning_trades': self.portfolio_performance.winning_trades,
                'losing_trades': self.portfolio_performance.losing_trades,
                'win_rate': self.portfolio_performance.win_rate,
                'total_return': self.portfolio_performance.total_return,
                'max_drawdown': self.portfolio_performance.max_drawdown,
                'sharpe_ratio': self.portfolio_performance.sharpe_ratio
            },
            'current_status': {
                'trading_session': current_session,
                'session_enabled': session_config['enabled'],
                'allowed_pairs': session_config['pairs'],
                'daily_trades': self.daily_trades,
                'daily_pnl': self.daily_pnl
            },
            'expected_performance': {
                'conservative_annual_return': 66,
                'realistic_annual_return': 88,
                'optimistic_annual_return': 120,
                'portfolio_win_rate': 80.4,
                'portfolio_sharpe_ratio': 34.5,
                'total_expected_annual_return': 140
            }
        }

# Global instance
_multi_strategy_portfolio = None

def get_multi_strategy_portfolio():
    """Get Multi-Strategy Portfolio instance"""
    global _multi_strategy_portfolio
    if _multi_strategy_portfolio is None:
        _multi_strategy_portfolio = MultiStrategyPortfolio()
    return _multi_strategy_portfolio
