#!/usr/bin/env python3
"""
Signal Tracker - Tracks trading signals throughout their lifecycle
Stores pending signals, active trades, and completed signals with metadata and AI insights
"""
import logging
import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
import uuid

logger = logging.getLogger(__name__)

class SignalStatus(Enum):
    """Signal status enumeration"""
    PENDING = "pending"      # Waiting for entry
    ACTIVE = "active"        # Trade is open
    FILLED = "filled"        # Take profit hit
    STOPPED = "stopped"      # Stop loss hit
    CANCELLED = "cancelled"  # Signal cancelled/expired
    EXPIRED = "expired"      # Signal expired (timeout)

@dataclass
class SignalMetadata:
    """Metadata about signal generation"""
    signal_id: str
    instrument: str
    side: str  # 'BUY' or 'SELL'
    strategy_name: str
    entry_price: float
    stop_loss: float
    take_profit: float
    generated_at: datetime
    status: SignalStatus = SignalStatus.PENDING
    
    # AI Insights
    ai_insight: str = ""
    conditions_met: List[str] = field(default_factory=list)
    indicators: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    risk_reward_ratio: float = 0.0
    
    # Trade execution info (filled when trade opens)
    trade_id: Optional[str] = None
    executed_at: Optional[datetime] = None
    actual_entry_price: Optional[float] = None
    
    # Real-time tracking
    current_price: Optional[float] = None
    unrealized_pl: Optional[float] = None
    pips_away: Optional[float] = None
    pips_to_sl: Optional[float] = None
    pips_to_tp: Optional[float] = None
    
    # Closure info
    closed_at: Optional[datetime] = None
    exit_price: Optional[float] = None
    realized_pl: Optional[float] = None
    
    # Account info
    account_id: Optional[str] = None
    units: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['status'] = self.status.value
        data['generated_at'] = self.generated_at.isoformat() if self.generated_at else None
        data['executed_at'] = self.executed_at.isoformat() if self.executed_at else None
        data['closed_at'] = self.closed_at.isoformat() if self.closed_at else None
        return data

class SignalTracker:
    """
    Tracks all trading signals throughout their lifecycle
    Singleton pattern for global access
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.signals: Dict[str, SignalMetadata] = {}
        self.max_signals = 100  # Keep last 100 signals in memory
        self.expiry_hours = 1  # Signals expire after 1 hour
        self._lock = threading.Lock()
        self._initialized = True
        
        logger.info("✅ SignalTracker initialized")
    
    def add_signal(self, 
                   instrument: str,
                   side: str,
                   strategy_name: str,
                   entry_price: float,
                   stop_loss: float,
                   take_profit: float,
                   ai_insight: str = "",
                   conditions_met: List[str] = None,
                   indicators: Dict[str, Any] = None,
                   confidence: float = 1.0,
                   account_id: str = None,
                   units: int = None) -> str:
        """
        Add a new trading signal
        
        Returns:
            signal_id: Unique identifier for the signal
        """
        with self._lock:
            signal_id = str(uuid.uuid4())
            
            # Calculate risk/reward ratio
            from src.utils.pips_calculator import calculate_risk_reward_ratio
            risk_pips, reward_pips, rr_ratio = calculate_risk_reward_ratio(
                entry_price, stop_loss, take_profit, instrument
            )
            
            signal = SignalMetadata(
                signal_id=signal_id,
                instrument=instrument,
                side=side,
                strategy_name=strategy_name,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                generated_at=datetime.now(timezone.utc),
                ai_insight=ai_insight,
                conditions_met=conditions_met or [],
                indicators=indicators or {},
                confidence=confidence,
                risk_reward_ratio=rr_ratio,
                account_id=account_id,
                units=units
            )
            
            self.signals[signal_id] = signal
            
            # Cleanup old signals if exceeding max
            self._cleanup_old_signals()
            
            logger.info(f"📊 Signal added: {signal_id} - {instrument} {side} @ {entry_price}")
            return signal_id
    
    def update_signal_status(self, signal_id: str, status: SignalStatus, **kwargs) -> bool:
        """
        Update signal status and related fields
        
        Args:
            signal_id: Signal identifier
            status: New status
            **kwargs: Additional fields to update (trade_id, executed_at, etc.)
            
        Returns:
            True if updated successfully
        """
        with self._lock:
            if signal_id not in self.signals:
                logger.warning(f"⚠️ Signal {signal_id} not found")
                return False
            
            signal = self.signals[signal_id]
            signal.status = status
            
            # Update timestamp based on status
            if status == SignalStatus.ACTIVE and 'executed_at' not in kwargs:
                kwargs['executed_at'] = datetime.now(timezone.utc)
            elif status in [SignalStatus.FILLED, SignalStatus.STOPPED, SignalStatus.CANCELLED]:
                if 'closed_at' not in kwargs:
                    kwargs['closed_at'] = datetime.now(timezone.utc)
            
            # Update all provided fields
            for key, value in kwargs.items():
                if hasattr(signal, key):
                    setattr(signal, key, value)
            
            logger.info(f"✅ Signal {signal_id} updated to {status.value}")
            return True
    
    def update_signal_price(self, signal_id: str, current_price: float, 
                           unrealized_pl: float = None) -> bool:
        """
        Update current price and calculated fields for a signal
        
        Args:
            signal_id: Signal identifier
            current_price: Current market price
            unrealized_pl: Current unrealized P/L (for active trades)
            
        Returns:
            True if updated successfully
        """
        with self._lock:
            if signal_id not in self.signals:
                return False
            
            signal = self.signals[signal_id]
            signal.current_price = current_price
            
            if unrealized_pl is not None:
                signal.unrealized_pl = unrealized_pl
            
            # Calculate pips
            from src.utils.pips_calculator import calculate_pips, calculate_pips_to_target
            
            if signal.status == SignalStatus.PENDING:
                # Pips away from entry
                signal.pips_away = calculate_pips(signal.instrument, current_price, signal.entry_price)
            elif signal.status == SignalStatus.ACTIVE:
                # Pips to SL and TP
                signal.pips_to_sl = calculate_pips_to_target(current_price, signal.stop_loss, signal.instrument)
                signal.pips_to_tp = calculate_pips_to_target(current_price, signal.take_profit, signal.instrument)
            
            return True
    
    def get_signal(self, signal_id: str) -> Optional[SignalMetadata]:
        """Get a specific signal by ID"""
        with self._lock:
            return self.signals.get(signal_id)
    
    def get_pending_signals(self, instrument: str = None, strategy: str = None) -> List[SignalMetadata]:
        """
        Get all pending signals with optional filtering
        
        Args:
            instrument: Filter by instrument
            strategy: Filter by strategy name
            
        Returns:
            List of pending signals
        """
        with self._lock:
            signals = [s for s in self.signals.values() if s.status == SignalStatus.PENDING]
            
            if instrument:
                signals = [s for s in signals if s.instrument == instrument]
            if strategy:
                signals = [s for s in signals if s.strategy_name == strategy]
            
            # Sort by time (newest first)
            signals.sort(key=lambda x: x.generated_at, reverse=True)
            
            return signals
    
    def get_active_signals(self, instrument: str = None, strategy: str = None) -> List[SignalMetadata]:
        """
        Get all active signals (open trades) with optional filtering
        
        Args:
            instrument: Filter by instrument
            strategy: Filter by strategy name
            
        Returns:
            List of active signals
        """
        with self._lock:
            signals = [s for s in self.signals.values() if s.status == SignalStatus.ACTIVE]
            
            if instrument:
                signals = [s for s in signals if s.instrument == instrument]
            if strategy:
                signals = [s for s in signals if s.strategy_name == strategy]
            
            # Sort by execution time (newest first)
            signals.sort(key=lambda x: x.executed_at or x.generated_at, reverse=True)
            
            return signals
    
    def get_all_signals(self, status: SignalStatus = None, instrument: str = None, 
                       strategy: str = None, limit: int = 50) -> List[SignalMetadata]:
        """
        Get all signals with optional filtering
        
        Args:
            status: Filter by status
            instrument: Filter by instrument
            strategy: Filter by strategy name
            limit: Maximum number of signals to return
            
        Returns:
            List of signals
        """
        with self._lock:
            signals = list(self.signals.values())
            
            if status:
                signals = [s for s in signals if s.status == status]
            if instrument:
                signals = [s for s in signals if s.instrument == instrument]
            if strategy:
                signals = [s for s in signals if s.strategy_name == strategy]
            
            # Sort by time (newest first)
            signals.sort(key=lambda x: x.generated_at, reverse=True)
            
            return signals[:limit]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about signals"""
        with self._lock:
            total = len(self.signals)
            pending = len([s for s in self.signals.values() if s.status == SignalStatus.PENDING])
            active = len([s for s in self.signals.values() if s.status == SignalStatus.ACTIVE])
            filled = len([s for s in self.signals.values() if s.status == SignalStatus.FILLED])
            stopped = len([s for s in self.signals.values() if s.status == SignalStatus.STOPPED])
            
            # Calculate win rate
            closed_trades = filled + stopped
            win_rate = (filled / closed_trades * 100) if closed_trades > 0 else 0
            
            # Calculate average hold time for closed trades
            closed_signals = [s for s in self.signals.values() 
                            if s.status in [SignalStatus.FILLED, SignalStatus.STOPPED] 
                            and s.executed_at and s.closed_at]
            
            if closed_signals:
                durations = [(s.closed_at - s.executed_at).total_seconds() / 60 
                           for s in closed_signals]
                avg_hold_time = sum(durations) / len(durations)
            else:
                avg_hold_time = 0
            
            return {
                'total_signals': total,
                'pending': pending,
                'active': active,
                'filled': filled,
                'stopped': stopped,
                'win_rate': round(win_rate, 1),
                'avg_hold_time_minutes': round(avg_hold_time, 1)
            }
    
    def _cleanup_old_signals(self):
        """Remove old signals to maintain memory limit"""
        if len(self.signals) <= self.max_signals:
            return
        
        # Sort by time and remove oldest
        sorted_signals = sorted(
            self.signals.items(),
            key=lambda x: x[1].generated_at,
            reverse=True
        )
        
        # Keep only max_signals newest
        self.signals = dict(sorted_signals[:self.max_signals])
        
        logger.info(f"🧹 Cleaned up old signals, kept {len(self.signals)}")
    
    def expire_old_pending_signals(self):
        """Mark old pending signals as expired"""
        with self._lock:
            now = datetime.now(timezone.utc)
            expiry_time = timedelta(hours=self.expiry_hours)
            
            expired_count = 0
            for signal in self.signals.values():
                if signal.status == SignalStatus.PENDING:
                    age = now - signal.generated_at
                    if age > expiry_time:
                        signal.status = SignalStatus.EXPIRED
                        expired_count += 1
            
            if expired_count > 0:
                logger.info(f"⏰ Expired {expired_count} old pending signals")


# Singleton getter
_signal_tracker_instance = None

def get_signal_tracker() -> SignalTracker:
    """Get the global SignalTracker instance"""
    global _signal_tracker_instance
    if _signal_tracker_instance is None:
        _signal_tracker_instance = SignalTracker()
    return _signal_tracker_instance



