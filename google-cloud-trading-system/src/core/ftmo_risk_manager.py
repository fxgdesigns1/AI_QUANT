#!/usr/bin/env python3
"""
FTMO Risk Manager
Implements strict FTMO challenge rules and risk management
"""

import logging
from datetime import datetime, date
from typing import Dict, Optional, Tuple
from dataclasses import dataclass, field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class FTMOAccount:
    """FTMO account state tracking"""
    initial_balance: float
    current_balance: float
    peak_balance: float
    daily_start_balance: float
    daily_peak_balance: float
    trades_today: int = 0
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    consecutive_losses: int = 0
    max_consecutive_losses: int = 0
    last_trade_date: Optional[date] = None
    start_date: date = field(default_factory=lambda: datetime.now().date())
    trading_days: int = 0

class FTMORiskManager:
    """
    FTMO Challenge Risk Manager
    
    FTMO Phase 1 Rules:
    - Starting Balance: $100,000
    - Profit Target: $10,000 (10%)
    - Maximum Daily Loss: $5,000 (5%)
    - Maximum Loss: $10,000 (10%)
    - Minimum Trading Days: 4
    - Maximum Trading Days: Unlimited
    
    FTMO Phase 2 Rules:
    - Starting Balance: $100,000
    - Profit Target: $5,000 (5%)
    - Maximum Daily Loss: $5,000 (5%)
    - Maximum Loss: $10,000 (10%)
    - Minimum Trading Days: 4
    - Maximum Trading Days: Unlimited
    """
    
    # FTMO Constants
    MAX_DAILY_DRAWDOWN = 0.05  # 5%
    MAX_TOTAL_DRAWDOWN = 0.10  # 10%
    PHASE_1_TARGET = 0.10  # 10%
    PHASE_2_TARGET = 0.05  # 5%
    MIN_TRADING_DAYS = 4
    
    # Conservative Trading Limits
    MAX_RISK_PER_TRADE = 0.005  # 0.5% per trade
    MAX_DAILY_TRADES = 5
    MAX_CONCURRENT_POSITIONS = 2
    MAX_TOTAL_EXPOSURE = 0.02  # 2% total exposure
    MIN_RISK_REWARD_RATIO = 2.0  # 1:2 minimum
    
    def __init__(self, initial_balance: float = 100000, phase: int = 1):
        """Initialize FTMO risk manager"""
        self.phase = phase
        self.account = FTMOAccount(
            initial_balance=initial_balance,
            current_balance=initial_balance,
            peak_balance=initial_balance,
            daily_start_balance=initial_balance,
            daily_peak_balance=initial_balance
        )
        
        # Set profit target based on phase
        self.profit_target = self.PHASE_1_TARGET if phase == 1 else self.PHASE_2_TARGET
        
        logger.info(f"✅ FTMO Risk Manager initialized - Phase {phase}")
        logger.info(f"   Initial Balance: ${initial_balance:,.2f}")
        logger.info(f"   Profit Target: ${initial_balance * self.profit_target:,.2f} ({self.profit_target*100}%)")
        logger.info(f"   Max Daily Loss: ${initial_balance * self.MAX_DAILY_DRAWDOWN:,.2f} ({self.MAX_DAILY_DRAWDOWN*100}%)")
        logger.info(f"   Max Total Loss: ${initial_balance * self.MAX_TOTAL_DRAWDOWN:,.2f} ({self.MAX_TOTAL_DRAWDOWN*100}%)")
        logger.info(f"   Max Risk/Trade: {self.MAX_RISK_PER_TRADE*100}%")
        logger.info(f"   Max Positions: {self.MAX_CONCURRENT_POSITIONS}")
    
    def check_daily_drawdown(self) -> Tuple[bool, float, float]:
        """
        Check if daily drawdown limit has been breached
        
        Returns:
            (can_trade, current_drawdown, remaining_buffer)
        """
        current_drawdown = (self.account.daily_start_balance - self.account.current_balance) / self.account.daily_start_balance
        remaining_buffer = self.MAX_DAILY_DRAWDOWN - current_drawdown
        
        can_trade = current_drawdown < self.MAX_DAILY_DRAWDOWN
        
        return can_trade, current_drawdown, remaining_buffer
    
    def check_total_drawdown(self) -> Tuple[bool, float, float]:
        """
        Check if total drawdown limit has been breached
        
        Returns:
            (can_trade, current_drawdown, remaining_buffer)
        """
        current_drawdown = (self.account.peak_balance - self.account.current_balance) / self.account.peak_balance
        remaining_buffer = self.MAX_TOTAL_DRAWDOWN - current_drawdown
        
        can_trade = current_drawdown < self.MAX_TOTAL_DRAWDOWN
        
        return can_trade, current_drawdown, remaining_buffer
    
    def can_trade(self, open_positions: int = 0) -> Tuple[bool, str]:
        """
        Check if trading is allowed based on FTMO rules
        
        Returns:
            (can_trade, reason)
        """
        # Check daily drawdown
        daily_ok, daily_dd, daily_buffer = self.check_daily_drawdown()
        if not daily_ok:
            return False, f"Daily drawdown limit breached ({daily_dd*100:.2f}% >= {self.MAX_DAILY_DRAWDOWN*100}%)"
        
        # Check total drawdown
        total_ok, total_dd, total_buffer = self.check_total_drawdown()
        if not total_ok:
            return False, f"Total drawdown limit breached ({total_dd*100:.2f}% >= {self.MAX_TOTAL_DRAWDOWN*100}%)"
        
        # Check daily trade limit
        if self.account.trades_today >= self.MAX_DAILY_TRADES:
            return False, f"Daily trade limit reached ({self.account.trades_today}/{self.MAX_DAILY_TRADES})"
        
        # Check concurrent position limit
        if open_positions >= self.MAX_CONCURRENT_POSITIONS:
            return False, f"Max concurrent positions reached ({open_positions}/{self.MAX_CONCURRENT_POSITIONS})"
        
        # Check consecutive losses
        if self.account.consecutive_losses >= 3:
            return False, f"Too many consecutive losses ({self.account.consecutive_losses}), take a break"
        
        return True, "OK to trade"
    
    def calculate_position_size(self, entry_price: float, stop_loss: float, instrument: str = "XAU_USD") -> int:
        """
        Calculate conservative position size based on FTMO risk limits
        
        Returns:
            units to trade
        """
        # Calculate risk per trade in dollars
        risk_dollars = self.account.current_balance * self.MAX_RISK_PER_TRADE
        
        # Calculate pip value based on instrument
        if instrument == "XAU_USD":
            # Gold: 1 pip = $0.01 per unit
            pip_value = 0.01
            pip_size = 0.01  # $0.01 movement
        else:
            # Forex: 1 pip = $0.0001 movement, need to calculate pip value
            # For 1000 units, 1 pip = $0.10
            pip_value = 0.0001
            pip_size = 0.0001
        
        # Calculate stop loss distance in pips
        stop_distance = abs(entry_price - stop_loss)
        
        if stop_distance == 0:
            logger.error("❌ Stop distance is zero!")
            return 0
        
        # Calculate position size
        # risk_dollars = units * pip_value * (stop_distance / pip_size)
        # units = risk_dollars / (pip_value * (stop_distance / pip_size))
        
        if instrument == "XAU_USD":
            # Gold calculation
            units = int(risk_dollars / stop_distance)
        else:
            # Forex calculation
            pips_at_risk = stop_distance / pip_size
            units = int(risk_dollars / (pip_value * pips_at_risk * 1000)) * 1000
        
        # Ensure minimum viable position
        if instrument == "XAU_USD":
            units = max(1, units)
        else:
            units = max(1000, units)
        
        logger.info(f"📊 Position size calculated: {units} units (risk: ${risk_dollars:.2f})")
        
        return units
    
    def validate_trade(self, entry_price: float, stop_loss: float, take_profit: float, 
                      instrument: str = "XAU_USD", open_positions: int = 0) -> Tuple[bool, str, int]:
        """
        Validate if a trade meets FTMO requirements
        
        Returns:
            (is_valid, reason, position_size)
        """
        # Check if trading is allowed
        can_trade, reason = self.can_trade(open_positions)
        if not can_trade:
            return False, reason, 0
        
        # Calculate risk-reward ratio
        risk = abs(entry_price - stop_loss)
        reward = abs(take_profit - entry_price)
        
        if risk == 0:
            return False, "Invalid stop loss (zero risk)", 0
        
        rr_ratio = reward / risk
        
        if rr_ratio < self.MIN_RISK_REWARD_RATIO:
            return False, f"Risk-reward ratio too low ({rr_ratio:.2f} < {self.MIN_RISK_REWARD_RATIO})", 0
        
        # Calculate position size
        position_size = self.calculate_position_size(entry_price, stop_loss, instrument)
        
        if position_size == 0:
            return False, "Position size calculation failed", 0
        
        return True, f"Trade approved (R:R {rr_ratio:.2f})", position_size
    
    def record_trade_entry(self, instrument: str, side: str, entry_price: float, 
                          stop_loss: float, take_profit: float, units: int):
        """Record trade entry"""
        today = datetime.now().date()
        
        # Reset daily counters if new day
        if self.account.last_trade_date != today:
            self.account.trades_today = 0
            self.account.daily_start_balance = self.account.current_balance
            self.account.daily_peak_balance = self.account.current_balance
            self.account.trading_days += 1
            self.account.last_trade_date = today
            logger.info(f"📅 New trading day {self.account.trading_days}")
        
        self.account.trades_today += 1
        self.account.total_trades += 1
        
        logger.info(f"📝 Trade entered: {instrument} {side} @ {entry_price}")
        logger.info(f"   Units: {units}, SL: {stop_loss}, TP: {take_profit}")
        logger.info(f"   Trades today: {self.account.trades_today}/{self.MAX_DAILY_TRADES}")
    
    def record_trade_exit(self, profit_loss: float, is_win: bool):
        """Record trade exit and update account state"""
        # Update balance
        self.account.current_balance += profit_loss
        
        # Update peak balance
        if self.account.current_balance > self.account.peak_balance:
            self.account.peak_balance = self.account.current_balance
        
        # Update daily peak
        if self.account.current_balance > self.account.daily_peak_balance:
            self.account.daily_peak_balance = self.account.current_balance
        
        # Update win/loss stats
        if is_win:
            self.account.wins += 1
            self.account.consecutive_losses = 0
        else:
            self.account.losses += 1
            self.account.consecutive_losses += 1
            if self.account.consecutive_losses > self.account.max_consecutive_losses:
                self.account.max_consecutive_losses = self.account.consecutive_losses
        
        # Log results
        win_rate = (self.account.wins / self.account.total_trades * 100) if self.account.total_trades > 0 else 0
        profit = self.account.current_balance - self.account.initial_balance
        profit_pct = (profit / self.account.initial_balance) * 100
        
        logger.info(f"{'✅' if is_win else '❌'} Trade closed: ${profit_loss:+,.2f}")
        logger.info(f"   Balance: ${self.account.current_balance:,.2f}")
        logger.info(f"   Profit: ${profit:+,.2f} ({profit_pct:+.2f}%)")
        logger.info(f"   Win Rate: {self.account.wins}/{self.account.total_trades} ({win_rate:.1f}%)")
    
    def get_status_report(self) -> Dict:
        """Get comprehensive FTMO status report"""
        # Calculate metrics
        profit = self.account.current_balance - self.account.initial_balance
        profit_pct = (profit / self.account.initial_balance) * 100
        target_profit = self.account.initial_balance * self.profit_target
        target_remaining = target_profit - profit
        
        daily_dd_ok, daily_dd, daily_buffer = self.check_daily_drawdown()
        total_dd_ok, total_dd, total_buffer = self.check_total_drawdown()
        
        win_rate = (self.account.wins / self.account.total_trades * 100) if self.account.total_trades > 0 else 0
        
        # Calculate estimated days to target
        if self.account.trading_days > 0 and profit > 0:
            avg_daily_profit = profit / self.account.trading_days
            days_to_target = max(0, target_remaining / avg_daily_profit) if avg_daily_profit > 0 else float('inf')
        else:
            days_to_target = float('inf')
        
        # Determine status
        if profit >= target_profit and self.account.trading_days >= self.MIN_TRADING_DAYS:
            status = "PASSED"
        elif not daily_dd_ok or not total_dd_ok:
            status = "FAILED"
        else:
            status = "IN_PROGRESS"
        
        return {
            'phase': self.phase,
            'status': status,
            'balance': self.account.current_balance,
            'profit': profit,
            'profit_pct': profit_pct,
            'target_profit': target_profit,
            'target_remaining': target_remaining,
            'progress_to_target': min(100, (profit / target_profit) * 100) if target_profit > 0 else 0,
            'daily_drawdown': daily_dd,
            'daily_drawdown_pct': daily_dd * 100,
            'daily_buffer': daily_buffer,
            'daily_buffer_pct': daily_buffer * 100,
            'total_drawdown': total_dd,
            'total_drawdown_pct': total_dd * 100,
            'total_buffer': total_buffer,
            'total_buffer_pct': total_buffer * 100,
            'trading_days': self.account.trading_days,
            'total_trades': self.account.total_trades,
            'trades_today': self.account.trades_today,
            'wins': self.account.wins,
            'losses': self.account.losses,
            'win_rate': win_rate,
            'consecutive_losses': self.account.consecutive_losses,
            'max_consecutive_losses': self.account.max_consecutive_losses,
            'days_to_target_estimate': days_to_target if days_to_target != float('inf') else None
        }
    
    def format_status_message(self) -> str:
        """Format status report for Telegram"""
        report = self.get_status_report()
        
        status_emoji = {
            'PASSED': '🎉',
            'FAILED': '❌',
            'IN_PROGRESS': '🔄'
        }
        
        message = f"""<b>FTMO Phase {report['phase']} Status</b> {status_emoji.get(report['status'], '📊')}

<b>Account Status:</b>
Balance: ${report['balance']:,.2f}
Profit: ${report['profit']:+,.2f} ({report['profit_pct']:+.2f}%)
Target: ${report['target_profit']:,.2f} ({report['progress_to_target']:.1f}% complete)
Remaining: ${report['target_remaining']:,.2f}

<b>Drawdown Status:</b>
Daily: {report['daily_drawdown_pct']:.2f}% / 5.00% (buffer: {report['daily_buffer_pct']:.2f}%)
Total: {report['total_drawdown_pct']:.2f}% / 10.00% (buffer: {report['total_buffer_pct']:.2f}%)

<b>Trading Stats:</b>
Trading Days: {report['trading_days']} (min {self.MIN_TRADING_DAYS} required)
Total Trades: {report['total_trades']}
Trades Today: {report['trades_today']}/{self.MAX_DAILY_TRADES}
Win Rate: {report['wins']}/{report['total_trades']} ({report['win_rate']:.1f}%)
Consecutive Losses: {report['consecutive_losses']} (max: {report['max_consecutive_losses']})

<b>Projections:</b>"""
        
        if report['days_to_target_estimate']:
            message += f"\nEstimated Days to Target: {int(report['days_to_target_estimate'])}"
        else:
            message += "\nEstimated Days to Target: N/A (need more trading history)"
        
        return message
    
    def reset_daily_counters(self):
        """Reset daily counters at start of new trading day"""
        self.account.trades_today = 0
        self.account.daily_start_balance = self.account.current_balance
        self.account.daily_peak_balance = self.account.current_balance
        logger.info("🔄 Daily counters reset")

# Singleton instance
_ftmo_risk_manager = None

def get_ftmo_risk_manager(initial_balance: float = 100000, phase: int = 1) -> FTMORiskManager:
    """Get or create FTMO risk manager singleton"""
    global _ftmo_risk_manager
    if _ftmo_risk_manager is None:
        _ftmo_risk_manager = FTMORiskManager(initial_balance, phase)
    return _ftmo_risk_manager




