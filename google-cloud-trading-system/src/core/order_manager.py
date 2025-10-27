#!/usr/bin/env python3
"""
Order Management System - CORRECTED VERSION
Production-ready order management for Google Cloud deployment
FIXED: Uses account-specific environment variables, 75% portfolio risk, and proper imports
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any  # FIXED: Added Any import
from dataclasses import dataclass, asdict
from enum import Enum

from .oanda_client import OandaClient, OandaOrder, OandaPosition, get_oanda_client

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OrderStatus(Enum):
    """Order status enumeration"""
    PENDING = "PENDING"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"

class OrderSide(Enum):
    """Order side enumeration"""
    BUY = "BUY"
    SELL = "SELL"

# Alias for compatibility
Side = OrderSide

class OrderType(Enum):
    """Order type enumeration"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"

@dataclass
class TradeSignal:
    """Trading signal from strategy"""
    instrument: str
    side: OrderSide
    units: int
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    strategy_name: str = ""
    confidence: float = 1.0
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

@dataclass
class PositionSizing:
    """Position sizing calculation"""
    instrument: str
    account_balance: float
    risk_per_trade: float
    stop_loss_distance: float
    units: int
    position_value: float
    risk_amount: float

@dataclass
class TradeExecution:
    """Trade execution result"""
    signal: TradeSignal
    order: Optional[OandaOrder]
    success: bool
    error_message: Optional[str] = None
    execution_time: datetime = None
    
    def __post_init__(self):
        if self.execution_time is None:
            self.execution_time = datetime.now()

class OrderManager:
    """Production order management system for live trading - CORRECTED"""
    
    def __init__(self, account_id: str = None, max_risk_per_trade: float = None,
                 max_portfolio_risk: float = None, max_positions: int = None,
                 daily_trade_limit: int = None):
        """Initialize order manager with optional account-specific settings"""
        from .dynamic_account_manager import get_account_manager
        
        # Get account manager and client
        self.account_manager = get_account_manager()
        self.account_id = account_id or os.getenv('OANDA_ACCOUNT_ID')
        self.oanda_client = self.account_manager.get_account_client(self.account_id) if account_id else get_oanda_client()
        
        # CORRECTED: Use account-specific environment variables
        if account_id:
            # Determine which account this is and use appropriate env vars
            primary_account = os.getenv('PRIMARY_ACCOUNT')
            gold_account = os.getenv('GOLD_SCALP_ACCOUNT')
            alpha_account = os.getenv('STRATEGY_ALPHA_ACCOUNT')
            
            if account_id == primary_account:
                # PRIMARY account (Gold Scalping 5M)
                self.max_risk_per_trade = max_risk_per_trade or float(os.getenv('PRIMARY_MAX_RISK_PER_TRADE', '0.02'))
                self.max_portfolio_risk = max_portfolio_risk or float(os.getenv('PRIMARY_MAX_PORTFOLIO_RISK', '0.20'))  # SAFE: 20% MAX
                self.max_positions = max_positions or int(os.getenv('PRIMARY_MAX_POSITIONS', '5'))
                self.daily_trade_limit = daily_trade_limit or int(os.getenv('PRIMARY_DAILY_TRADE_LIMIT', '50'))
            elif account_id == gold_account:
                # GOLD_SCALP account (Ultra Strict Fx 15M)
                self.max_risk_per_trade = max_risk_per_trade or float(os.getenv('GOLD_MAX_RISK_PER_TRADE', '0.015'))
                self.max_portfolio_risk = max_portfolio_risk or float(os.getenv('GOLD_MAX_PORTFOLIO_RISK', '0.75'))  # CORRECTED: 75%
                self.max_positions = max_positions or int(os.getenv('GOLD_MAX_POSITIONS', '15'))
                self.daily_trade_limit = daily_trade_limit or int(os.getenv('GOLD_DAILY_TRADE_LIMIT', '100'))
            elif account_id == alpha_account:
                # STRATEGY_ALPHA account (Combined Portfolio)
                self.max_risk_per_trade = max_risk_per_trade or float(os.getenv('ALPHA_MAX_RISK_PER_TRADE', '0.025'))
                self.max_portfolio_risk = max_portfolio_risk or float(os.getenv('ALPHA_MAX_PORTFOLIO_RISK', '0.75'))  # CORRECTED: 75%
                self.max_positions = max_positions or int(os.getenv('ALPHA_MAX_POSITIONS', '7'))
                self.daily_trade_limit = daily_trade_limit or int(os.getenv('ALPHA_DAILY_TRADE_LIMIT', '30'))
            else:
                # Fallback to generic settings
                self.max_risk_per_trade = max_risk_per_trade or float(os.getenv('MAX_RISK_PER_TRADE', '0.02'))
                self.max_portfolio_risk = max_portfolio_risk or float(os.getenv('MAX_PORTFOLIO_RISK', '0.75'))  # CORRECTED: 75%
                self.max_positions = max_positions or int(os.getenv('MAX_POSITIONS', '5'))
                self.daily_trade_limit = daily_trade_limit or int(os.getenv('DAILY_TRADE_LIMIT', '50'))
        else:
            # Fallback to generic settings
            self.max_risk_per_trade = max_risk_per_trade or float(os.getenv('MAX_RISK_PER_TRADE', '0.02'))
            self.max_portfolio_risk = max_portfolio_risk or float(os.getenv('MAX_PORTFOLIO_RISK', '0.75'))  # CORRECTED: 75%
            self.max_positions = max_positions or int(os.getenv('MAX_POSITIONS', '5'))
            self.daily_trade_limit = daily_trade_limit or int(os.getenv('DAILY_TRADE_LIMIT', '50'))
        
        self.position_sizing_method = os.getenv('POSITION_SIZING_METHOD', 'risk_based')
        
        # Order tracking
        self.active_orders: Dict[str, OandaOrder] = {}
        self.trade_history: List[TradeExecution] = []
        self.position_sizes: Dict[str, PositionSizing] = {}
        
        # Daily tracking
        self.daily_trade_count = 0
        self.last_reset_date = datetime.now().date()
        
        # Performance tracking
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_profit = 0.0
        self.total_loss = 0.0
        
        # Reset daily counters if needed
        self._reset_daily_counters()
        
        logger.info(f"✅ Order manager initialized for account {self.account_id}")
        logger.info(f"📊 Max risk per trade: {self.max_risk_per_trade*100:.1f}%")
        logger.info(f"📊 Max portfolio risk: {self.max_portfolio_risk*100:.1f}%")
        logger.info(f"📊 Max positions: {self.max_positions}")
    
    def _reset_daily_counters(self):
        """Reset daily trade counters if new day"""
        current_date = datetime.now().date()
        if current_date > self.last_reset_date:
            self.daily_trade_count = 0
            self.last_reset_date = current_date
            logger.info("🔄 Daily trade counters reset")
    
    def calculate_position_size(self, signal: TradeSignal) -> Optional[PositionSizing]:
        """Calculate position size based on risk management rules and signal strength"""
        try:
            if not self.oanda_client:
                logger.error("❌ No OANDA client available for position sizing")
                return None
            
            # Get account info
            account_info = self.oanda_client.get_account_info()
            if not account_info:
                logger.error("❌ Failed to get account info for position sizing")
                return None
            
            # Get current price
            prices = self.oanda_client.get_current_prices([signal.instrument], force_refresh=True)
            current_price = prices.get(signal.instrument)
            if not current_price:
                logger.error(f"❌ Could not get price for {signal.instrument}")
                return None
            
            # Calculate stop loss distance
            if not signal.stop_loss:
                logger.error("❌ No stop loss provided")
                return None
            
            stop_loss_distance = abs(current_price.bid - signal.stop_loss)
            
            # SMART DYNAMIC POSITION SIZING BASED ON SIGNAL STRENGTH
            # Use signal confidence (0.0-1.0) to scale risk
            signal_strength = signal.confidence if hasattr(signal, 'confidence') else 0.5
            
            # Import position sizer with dynamic scaling
            from .position_sizing import get_position_sizer
            position_sizer = get_position_sizer()
            
            # Calculate position using smart scaling (0.3%-1% based on signal strength)
            pos_result = position_sizer.calculate_position_size(
                account_balance=account_info.balance,
                risk_percent=self.max_risk_per_trade * 100,  # Convert to percentage
                entry_price=current_price.bid,  # Extract bid price as float
                stop_loss=signal.stop_loss,
                instrument=signal.instrument,
                signal_strength=signal_strength  # Pass signal strength for dynamic sizing
            )
            
            units = pos_result.units
            risk_amount = pos_result.risk_amount
            position_value = units * current_price.bid
            
            logger.info(f"📊 Position calculated: {units} units, ${risk_amount:.2f} risk (signal: {signal_strength*100:.0f}%)")
            
            return PositionSizing(
                instrument=signal.instrument,
                account_balance=account_info.balance,
                risk_per_trade=self.max_risk_per_trade,
                stop_loss_distance=stop_loss_distance,
                units=units,
                position_value=position_value,
                risk_amount=risk_amount
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate position size: {e}")
            return None
    
    def validate_trade(self, signal: TradeSignal, position_size: PositionSizing) -> Tuple[bool, str]:
        """Validate trade against risk management rules"""
        try:
            # Check daily trade limit
            if self.daily_trade_count >= self.daily_trade_limit:
                return False, f"Daily trade limit reached: {self.daily_trade_count}/{self.daily_trade_limit}"
            
            # Check position count
            current_positions = len(self.active_orders)
            if current_positions >= self.max_positions:
                return False, f"Maximum positions reached: {current_positions}/{self.max_positions}"
            
            # Check portfolio risk
            if self.oanda_client:
                account_info = self.oanda_client.get_account_info()
                if account_info:
                    total_margin_used = account_info.margin_used
                    portfolio_risk = total_margin_used / account_info.balance
                    
                    if portfolio_risk + (position_size.risk_amount / account_info.balance) > self.max_portfolio_risk:
                        return False, f"Portfolio risk limit would be exceeded: {portfolio_risk*100:.1f}%"
            
            # Check individual position risk
            if position_size.risk_amount > account_info.balance * self.max_risk_per_trade:
                return False, f"Position risk exceeds limit: {position_size.risk_amount:.2f} > {account_info.balance * self.max_risk_per_trade:.2f}"
            
            return True, "Trade validation passed"
            
        except Exception as e:
            logger.error(f"❌ Trade validation failed: {e}")
            return False, f"Validation error: {e}"
    
    def execute_trade(self, signal: TradeSignal) -> TradeExecution:
        """Execute a trade signal"""
        try:
            # TRADE SIZE VALIDATION (NEW OCT 21, 2025)
            from .trade_size_validator import get_trade_size_validator
            validator = get_trade_size_validator()
            
            size_validation = validator.validate_trade_size(
                instrument=signal.instrument,
                units=signal.units,
                strategy_name=getattr(signal, 'strategy_name', 'Unknown')
            )
            
            if not size_validation['valid']:
                logger.warning(f"🚫 MICRO TRADE BLOCKED: {size_validation['reason']}")
                return TradeExecution(
                    signal=signal,
                    order=None,
                    success=False,
                    error_message=f"Trade size {abs(signal.units)} below minimum {size_validation['min_required']}"
                )
            
            # Calculate position size
            position_size = self.calculate_position_size(signal)
            if not position_size:
                return TradeExecution(
                    signal=signal,
                    order=None,
                    success=False,
                    error_message="Failed to calculate position size"
                )
            
            # Validate trade
            is_valid, validation_message = self.validate_trade(signal, position_size)
            if not is_valid:
                logger.warning(f"⚠️ Trade validation failed: {validation_message}")
                return TradeExecution(
                    signal=signal,
                    order=None,
                    success=False,
                    error_message=validation_message
                )
            
            # Create order
            order = self.oanda_client.create_order(
                instrument=signal.instrument,
                units=position_size.units,
                side=signal.side.value,
                order_type=OrderType.MARKET.value,
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit
            )
            
            if order:
                # Store order and update counters
                self.active_orders[order.order_id] = order
                self.daily_trade_count += 1
                self.position_sizes[order.order_id] = position_size
                
                logger.info(f"✅ Trade executed: {signal.instrument} {signal.side.value} {position_size.units} units")
                
                # Send Telegram trade alert (best-effort)
                try:
                    from .telegram_notifier import get_telegram_notifier
                    # Fetch a recent price for the alert
                    px = self.oanda_client.get_current_prices([signal.instrument]).get(signal.instrument)
                    price = (px.bid + px.ask)/2.0 if px else 0.0
                    notifier = get_telegram_notifier()
                    account_name = os.getenv('ACCOUNT_NAME', 'Demo Practice')
                    notifier.send_trade_alert(account_name, signal.instrument, signal.side.value, price, signal.confidence, signal.strategy_name)
                except Exception as e:
                    logger.warning(f"⚠️ Failed to send Telegram trade alert: {e}")
                
                return TradeExecution(
                    signal=signal,
                    order=order,
                    success=True
                )
            else:
                return TradeExecution(
                    signal=signal,
                    order=None,
                    success=False,
                    error_message="Failed to create order"
                )
                
        except Exception as e:
            logger.error(f"❌ Trade execution failed: {e}")
            return TradeExecution(
                signal=signal,
                order=None,
                success=False,
                error_message=str(e)
            )
    
    def execute_trades(self, signals: List[TradeSignal]) -> Dict[str, Any]:
        """Execute multiple trade signals"""
        try:
            executed_trades = []
            failed_trades = []
            
            for signal in signals:
                execution = self.execute_trade(signal)
                
                if execution.success:
                    executed_trades.append(execution)
                    self.trade_history.append(execution)
                else:
                    failed_trades.append(execution)
            
            return {
                'executed_trades': executed_trades,
                'failed_trades': failed_trades,
                'total_executed': len(executed_trades),
                'total_failed': len(failed_trades),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to execute trades: {e}")
            return {
                'error': str(e),
                'executed_trades': [],
                'failed_trades': [],
                'total_executed': 0,
                'total_failed': 0,
                'timestamp': datetime.now().isoformat()
            }
    
    def get_trading_metrics(self) -> Dict[str, Any]:
        """Get trading performance metrics"""
        try:
            total_trades = len(self.trade_history)
            
            if total_trades > 0:
                win_rate = (self.winning_trades / total_trades) * 100
                profit_factor = self.total_profit / max(self.total_loss, 1)
            else:
                win_rate = 0.0
                profit_factor = 0.0
            
            return {
                'total_trades': total_trades,
                'winning_trades': self.winning_trades,
                'losing_trades': self.losing_trades,
                'win_rate': win_rate,
                'total_profit': self.total_profit,
                'total_loss': self.total_loss,
                'profit_factor': profit_factor,
                'daily_trade_count': self.daily_trade_count,
                'daily_trade_limit': self.daily_trade_limit,
                'active_positions': len(self.active_orders),
                'max_positions': self.max_positions,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get trading metrics: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def get_active_orders(self) -> List[OandaOrder]:
        """Get list of active orders"""
        return list(self.active_orders.values())
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an active order"""
        try:
            if order_id in self.active_orders:
                order = self.active_orders[order_id]
                success = self.oanda_client.cancel_order(order_id)
                
                if success:
                    del self.active_orders[order_id]
                    if order_id in self.position_sizes:
                        del self.position_sizes[order_id]
                    logger.info(f"✅ Order cancelled: {order_id}")
                    return True
                else:
                    logger.error(f"❌ Failed to cancel order: {order_id}")
                    return False
            else:
                logger.warning(f"⚠️ Order not found: {order_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error cancelling order {order_id}: {e}")
            return False
    
    def close_position(self, instrument: str) -> bool:
        """Close a position for a specific instrument"""
        try:
            if not self.oanda_client:
                logger.error("❌ No OANDA client available")
                return False
            
            # Get current position
            position = self.oanda_client.get_position(instrument)
            if not position:
                logger.warning(f"⚠️ No position found for {instrument}")
                return False
            
            # Close position
            success = self.oanda_client.close_position(instrument)
            
            if success:
                logger.info(f"✅ Position closed: {instrument}")
                return True
            else:
                logger.error(f"❌ Failed to close position: {instrument}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error closing position {instrument}: {e}")
            return False
    
    def get_account_summary(self) -> Dict[str, Any]:
        """Get account summary information"""
        try:
            if not self.oanda_client:
                return {
                    'error': 'No OANDA client available',
                    'timestamp': datetime.now().isoformat()
                }
            
            account_info = self.oanda_client.get_account_info()
            if not account_info:
                return {
                    'error': 'Failed to get account info',
                    'timestamp': datetime.now().isoformat()
                }
            
            return {
                'account_id': self.account_id,
                'balance': account_info.balance,
                'currency': account_info.currency,
                'unrealized_pl': account_info.unrealized_pl,
                'realized_pl': account_info.realized_pl,
                'margin_used': account_info.margin_used,
                'margin_available': account_info.margin_available,
                'open_trade_count': account_info.open_trade_count,
                'open_position_count': account_info.open_position_count,
                'active_orders': len(self.active_orders),
                'daily_trades': self.daily_trade_count,
                'daily_limit': self.daily_trade_limit,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get account summary: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

# Global order manager instances
_order_managers: Dict[str, OrderManager] = {}

def get_order_manager(account_id: str = None) -> OrderManager:
    """Get or create order manager for specific account"""
    if account_id is None:
        account_id = os.getenv('OANDA_ACCOUNT_ID')
    
    if account_id not in _order_managers:
        _order_managers[account_id] = OrderManager(account_id)
    
    return _order_managers[account_id]
