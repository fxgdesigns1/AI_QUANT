from datetime import datetime
#!/usr/bin/env python3
"""
Trade Approver - Telegram-based Manual Trade Approval
Enables hybrid execution with manual approval via Telegram
"""

import logging
import json
import time
import threading
import asyncio
import os
from typing import Dict, List, Optional, Tuple, Any, Callable
from enum import Enum
from dataclasses import dataclass
import uuid
from datetime import datetime, timedelta

# Import local modules
try:
    from .telegram_notifier import TelegramNotifier
    from .oanda_client import OandaClient
    from .quality_scoring import get_quality_scoring, QualityScore
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ApprovalStatus(Enum):
    """Trade approval status"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    AUTO_APPROVED = "auto_approved"
    AUTO_REJECTED = "auto_rejected"

@dataclass
class TradeApprovalRequest:
    """Trade approval request structure"""
    request_id: str
    instrument: str
    side: str
    entry_price: float
    stop_loss: float
    take_profit: float
    units: int
    quality_score: QualityScore
    timestamp: datetime
    expiry: datetime
    status: ApprovalStatus = ApprovalStatus.PENDING
    response_time: Optional[datetime] = None
    executed: bool = False
    execution_price: Optional[float] = None
    execution_time: Optional[datetime] = None
    execution_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

class TradeApprover:
    """
    Telegram-based manual trade approval system
    Enables hybrid execution with manual approval
    """
    
    def __init__(self):
        """Initialize trade approver"""
        self.name = "Trade Approver"
        
        # Approval settings
        self.approval_timeout_minutes = 10
        self.auto_approve_threshold = 85  # Auto-approve trades with quality >= 85
        self.auto_reject_threshold = 40   # Auto-reject trades with quality < 40
        self.max_concurrent_requests = 5
        
        # Storage for approval requests
        self.approval_requests: Dict[str, TradeApprovalRequest] = {}
        self.pending_requests: List[str] = []
        
        # Callbacks
        self.on_approved_callback: Optional[Callable[[TradeApprovalRequest], None]] = None
        self.on_rejected_callback: Optional[Callable[[TradeApprovalRequest], None]] = None
        
        # Initialize Telegram notifier if available
        self.telegram = None
        if TELEGRAM_AVAILABLE:
            try:
                self.telegram = TelegramNotifier()
                logger.info("✅ Telegram notifier initialized for trade approval")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Telegram notifier: {e}")
        
        # Start expiry checker thread
        self.stop_thread = False
        self.expiry_thread = threading.Thread(target=self._check_expired_requests)
        self.expiry_thread.daemon = True
        self.expiry_thread.start()
        
        logger.info(f"✅ {self.name} initialized")
    
    def request_approval(self, instrument: str, side: str, 
                        entry_price: float, stop_loss: float, take_profit: float,
                        units: int, quality_score: QualityScore,
                        context: Optional[Dict[str, Any]] = None) -> TradeApprovalRequest:
        """
        Request trade approval
        
        Args:
            instrument: Instrument to trade
            side: Trade direction ("BUY" or "SELL")
            entry_price: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit price
            units: Number of units to trade
            quality_score: Quality score object
            context: Optional additional context
            
        Returns:
            TradeApprovalRequest object
        """
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        
        # Create timestamp and expiry
        timestamp = datetime.now()
        expiry = timestamp + timedelta(minutes=self.approval_timeout_minutes)
        
        # Create approval request
        request = TradeApprovalRequest(
            request_id=request_id,
            instrument=instrument,
            side=side,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            units=units,
            quality_score=quality_score,
            timestamp=timestamp,
            expiry=expiry,
            context=context
        )
        
        # Store request
        self.approval_requests[request_id] = request
        self.pending_requests.append(request_id)
        
        # Check for auto-approval/rejection based on quality score
        if quality_score.total_score >= self.auto_approve_threshold:
            logger.info(f"🔄 Auto-approving high-quality trade: {instrument} {side} (Score: {quality_score.total_score})")
            self._auto_approve(request)
        elif quality_score.total_score < self.auto_reject_threshold:
            logger.info(f"🔄 Auto-rejecting low-quality trade: {instrument} {side} (Score: {quality_score.total_score})")
            self._auto_reject(request)
        else:
            # Send approval request via Telegram
            self._send_approval_request(request)
        
        return request
    
    def _auto_approve(self, request: TradeApprovalRequest):
        """
        Auto-approve a high-quality trade
        
        Args:
            request: TradeApprovalRequest to approve
        """
        request.status = ApprovalStatus.AUTO_APPROVED
        request.response_time = datetime.now()
        
        # Remove from pending
        if request.request_id in self.pending_requests:
            self.pending_requests.remove(request.request_id)
        
        # Send notification
        if self.telegram:
            self._send_auto_approval_notification(request)
        
        # Execute callback
        if self.on_approved_callback:
            self.on_approved_callback(request)
    
    def _auto_reject(self, request: TradeApprovalRequest):
        """
        Auto-reject a low-quality trade
        
        Args:
            request: TradeApprovalRequest to reject
        """
        request.status = ApprovalStatus.AUTO_REJECTED
        request.response_time = datetime.now()
        
        # Remove from pending
        if request.request_id in self.pending_requests:
            self.pending_requests.remove(request.request_id)
        
        # Send notification
        if self.telegram:
            self._send_auto_rejection_notification(request)
        
        # Execute callback
        if self.on_rejected_callback:
            self.on_rejected_callback(request)
    
    def _send_approval_request(self, request: TradeApprovalRequest):
        """
        Send approval request via Telegram
        
        Args:
            request: TradeApprovalRequest to send
        """
        if not self.telegram:
            logger.warning("⚠️ Telegram not available - cannot send approval request")
            return
        
        # Format risk and reward in currency
        risk = abs(request.entry_price - request.stop_loss) * request.units
        reward = abs(request.take_profit - request.entry_price) * request.units
        
        # Format message
        message = f"""🔔 **TRADE APPROVAL REQUEST**

**{request.instrument} {request.side}**
Quality: {request.quality_score.total_score}/100 ({request.quality_score.recommendation.upper()})

📊 **Trade Details:**
Entry: {request.entry_price:.5f}
Stop Loss: {request.stop_loss:.5f}
Take Profit: {request.take_profit:.5f}
Units: {request.units:,}

💰 **Risk/Reward:**
Risk: ${risk:.2f}
Reward: ${reward:.2f}
R:R Ratio: 1:{(reward/risk):.1f}

📈 **Quality Factors:**
{request.quality_score.explanation}

⏰ **Expires:** {request.expiry.strftime('%H:%M:%S')}
🆔 Request ID: {request.request_id[:8]}

**To approve:** /approve_{request.request_id[:8]}
**To reject:** /reject_{request.request_id[:8]}"""

        # Add context information if available
        if request.context:
            # Add market regime if available
            if "regime" in request.context:
                message += f"\n\n📊 **Market Regime:** {request.context['regime']}"
            
            # Add nearest support/resistance if available
            if "nearest_support" in request.context and "nearest_resistance" in request.context:
                message += f"\n\n📏 **Key Levels:**"
                message += f"\nSupport: {request.context['nearest_support']:.5f}"
                message += f"\nResistance: {request.context['nearest_resistance']:.5f}"
        
        # Send message
        try:
            self.telegram.send_trade_alert(f"Approval: {request.instrument} {request.side}", message)
            logger.info(f"✅ Sent approval request for {request.instrument} {request.side}")
        except Exception as e:
            logger.error(f"❌ Failed to send approval request: {e}")
    
    def _send_auto_approval_notification(self, request: TradeApprovalRequest):
        """
        Send auto-approval notification via Telegram
        
        Args:
            request: Auto-approved TradeApprovalRequest
        """
        message = f"""🔔 **TRADE AUTO-APPROVED**

**{request.instrument} {request.side}**
Quality: {request.quality_score.total_score}/100 (HIGH QUALITY)

📊 **Trade Details:**
Entry: {request.entry_price:.5f}
Stop Loss: {request.stop_loss:.5f}
Take Profit: {request.take_profit:.5f}
Units: {request.units:,}

💰 **Risk/Reward:**
R:R Ratio: 1:{((request.take_profit-request.entry_price)/(request.entry_price-request.stop_loss)):.1f}

⚙️ **Auto-approved:** High quality score exceeds threshold ({self.auto_approve_threshold})
🆔 Request ID: {request.request_id[:8]}"""

        try:
            self.telegram.send_trade_alert(f"Auto-Approved: {request.instrument} {request.side}", message)
        except Exception as e:
            logger.error(f"❌ Failed to send auto-approval notification: {e}")
    
    def _send_auto_rejection_notification(self, request: TradeApprovalRequest):
        """
        Send auto-rejection notification via Telegram
        
        Args:
            request: Auto-rejected TradeApprovalRequest
        """
        message = f"""🔔 **TRADE AUTO-REJECTED**

**{request.instrument} {request.side}**
Quality: {request.quality_score.total_score}/100 (LOW QUALITY)

📊 **Trade Details:**
Entry: {request.entry_price:.5f}
Stop Loss: {request.stop_loss:.5f}
Take Profit: {request.take_profit:.5f}

⚙️ **Auto-rejected:** Low quality score below threshold ({self.auto_reject_threshold})
🆔 Request ID: {request.request_id[:8]}"""

        try:
            self.telegram.send_trade_alert(f"Auto-Rejected: {request.instrument} {request.side}", message)
        except Exception as e:
            logger.error(f"❌ Failed to send auto-rejection notification: {e}")
    
    def approve_trade(self, request_id: str) -> bool:
        """
        Approve a trade
        
        Args:
            request_id: Request ID to approve (can be full ID or first 8 chars)
            
        Returns:
            True if approved, False if not found or already processed
        """
        # Find request by ID (full or partial)
        request = self._find_request(request_id)
        
        if not request or request.status != ApprovalStatus.PENDING:
            return False
        
        # Update status
        request.status = ApprovalStatus.APPROVED
        request.response_time = datetime.now()
        
        # Remove from pending
        if request.request_id in self.pending_requests:
            self.pending_requests.remove(request.request_id)
        
        # Send confirmation
        if self.telegram:
            self._send_approval_confirmation(request)
        
        # Execute callback
        if self.on_approved_callback:
            self.on_approved_callback(request)
        
        return True
    
    def reject_trade(self, request_id: str) -> bool:
        """
        Reject a trade
        
        Args:
            request_id: Request ID to reject (can be full ID or first 8 chars)
            
        Returns:
            True if rejected, False if not found or already processed
        """
        # Find request by ID (full or partial)
        request = self._find_request(request_id)
        
        if not request or request.status != ApprovalStatus.PENDING:
            return False
        
        # Update status
        request.status = ApprovalStatus.REJECTED
        request.response_time = datetime.now()
        
        # Remove from pending
        if request.request_id in self.pending_requests:
            self.pending_requests.remove(request.request_id)
        
        # Send confirmation
        if self.telegram:
            self._send_rejection_confirmation(request)
        
        # Execute callback
        if self.on_rejected_callback:
            self.on_rejected_callback(request)
        
        return True
    
    def _find_request(self, request_id: str) -> Optional[TradeApprovalRequest]:
        """
        Find request by ID (full or partial)
        
        Args:
            request_id: Request ID (full or first 8 chars)
            
        Returns:
            TradeApprovalRequest if found, None otherwise
        """
        # Check for exact match
        if request_id in self.approval_requests:
            return self.approval_requests[request_id]
        
        # Check for partial match (first 8 chars)
        for rid, request in self.approval_requests.items():
            if rid.startswith(request_id) or request_id.startswith(rid[:8]):
                return request
        
        return None
    
    def _send_approval_confirmation(self, request: TradeApprovalRequest):
        """
        Send approval confirmation via Telegram
        
        Args:
            request: Approved TradeApprovalRequest
        """
        message = f"""✅ **TRADE APPROVED**

**{request.instrument} {request.side}**
Quality: {request.quality_score.total_score}/100

📊 **Trade Details:**
Entry: {request.entry_price:.5f}
Stop Loss: {request.stop_loss:.5f}
Take Profit: {request.take_profit:.5f}
Units: {request.units:,}

⏱️ **Response Time:** {(request.response_time - request.timestamp).total_seconds():.1f} seconds
🆔 Request ID: {request.request_id[:8]}"""

        try:
            self.telegram.send_trade_alert(f"Approved: {request.instrument} {request.side}", message)
        except Exception as e:
            logger.error(f"❌ Failed to send approval confirmation: {e}")
    
    def _send_rejection_confirmation(self, request: TradeApprovalRequest):
        """
        Send rejection confirmation via Telegram
        
        Args:
            request: Rejected TradeApprovalRequest
        """
        message = f"""❌ **TRADE REJECTED**

**{request.instrument} {request.side}**
Quality: {request.quality_score.total_score}/100

📊 **Trade Details:**
Entry: {request.entry_price:.5f}
Stop Loss: {request.stop_loss:.5f}
Take Profit: {request.take_profit:.5f}

⏱️ **Response Time:** {(request.response_time - request.timestamp).total_seconds():.1f} seconds
🆔 Request ID: {request.request_id[:8]}"""

        try:
            self.telegram.send_trade_alert(f"Rejected: {request.instrument} {request.side}", message)
        except Exception as e:
            logger.error(f"❌ Failed to send rejection confirmation: {e}")
    
    def _check_expired_requests(self):
        """
        Background thread to check for expired requests
        """
        while not self.stop_thread:
            try:
                now = datetime.now()
                expired_ids = []
                
                # Check for expired requests
                for request_id in self.pending_requests:
                    request = self.approval_requests.get(request_id)
                    if request and now > request.expiry:
                        # Mark as expired
                        request.status = ApprovalStatus.EXPIRED
                        expired_ids.append(request_id)
                        
                        # Send notification
                        if self.telegram:
                            self._send_expiry_notification(request)
                
                # Remove expired requests from pending
                for request_id in expired_ids:
                    if request_id in self.pending_requests:
                        self.pending_requests.remove(request_id)
                
                # Sleep for a while
                time.sleep(10)
                
            except Exception as e:
                logger.error(f"❌ Error in expiry checker thread: {e}")
                time.sleep(30)  # Sleep longer on error
    
    def _send_expiry_notification(self, request: TradeApprovalRequest):
        """
        Send expiry notification via Telegram
        
        Args:
            request: Expired TradeApprovalRequest
        """
        message = f"""⏰ **TRADE REQUEST EXPIRED**

**{request.instrument} {request.side}**
Quality: {request.quality_score.total_score}/100

📊 **Trade Details:**
Entry: {request.entry_price:.5f}
Stop Loss: {request.stop_loss:.5f}
Take Profit: {request.take_profit:.5f}

⏱️ **Expired after:** {self.approval_timeout_minutes} minutes
🆔 Request ID: {request.request_id[:8]}"""

        try:
            self.telegram.send_trade_alert(f"Expired: {request.instrument} {request.side}", message)
        except Exception as e:
            logger.error(f"❌ Failed to send expiry notification: {e}")
    
    def mark_executed(self, request_id: str, execution_price: float, 
                     execution_id: str) -> bool:
        """
        Mark a trade as executed
        
        Args:
            request_id: Request ID
            execution_price: Execution price
            execution_id: Execution ID
            
        Returns:
            True if marked, False if not found
        """
        request = self._find_request(request_id)
        
        if not request:
            return False
        
        # Update execution details
        request.executed = True
        request.execution_price = execution_price
        request.execution_time = datetime.now()
        request.execution_id = execution_id
        
        # Send notification
        if self.telegram:
            self._send_execution_notification(request)
        
        return True
    
    def _send_execution_notification(self, request: TradeApprovalRequest):
        """
        Send execution notification via Telegram
        
        Args:
            request: Executed TradeApprovalRequest
        """
        # Calculate slippage
        slippage = 0
        if request.execution_price:
            slippage = (request.execution_price - request.entry_price) / request.entry_price * 100
            if request.side == "SELL":
                slippage = -slippage  # Reverse for sell orders
        
        message = f"""💰 **TRADE EXECUTED**

**{request.instrument} {request.side}**
Quality: {request.quality_score.total_score}/100

📊 **Execution Details:**
Requested Price: {request.entry_price:.5f}
Executed Price: {request.execution_price:.5f}
Slippage: {slippage:.4f}%
Units: {request.units:,}

⏱️ **Execution Time:** {request.execution_time.strftime('%H:%M:%S')}
🆔 Request ID: {request.request_id[:8]}
📝 Execution ID: {request.execution_id}"""

        try:
            self.telegram.send_trade_alert(f"Executed: {request.instrument} {request.side}", message)
        except Exception as e:
            logger.error(f"❌ Failed to send execution notification: {e}")
    
    def get_pending_requests(self) -> List[TradeApprovalRequest]:
        """
        Get list of pending approval requests
        
        Returns:
            List of pending TradeApprovalRequest objects
        """
        return [self.approval_requests[rid] for rid in self.pending_requests 
                if rid in self.approval_requests]
    
    def get_request(self, request_id: str) -> Optional[TradeApprovalRequest]:
        """
        Get a specific approval request
        
        Args:
            request_id: Request ID
            
        Returns:
            TradeApprovalRequest if found, None otherwise
        """
        return self._find_request(request_id)
    
    def get_recent_requests(self, hours: int = 24) -> List[TradeApprovalRequest]:
        """
        Get recent approval requests
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            List of recent TradeApprovalRequest objects
        """
        cutoff = datetime.now() - timedelta(hours=hours)
        return [r for r in self.approval_requests.values() if r.timestamp >= cutoff]
    
    def process_telegram_command(self, command: str) -> Optional[str]:
        """
        Process a Telegram command
        
        Args:
            command: Command string (e.g., "/approve_12345678")
            
        Returns:
            Response message or None if not a valid command
        """
        command = command.strip().lower()
        
        # Check for approval command
        if command.startswith("/approve_"):
            request_id = command[9:]  # Extract ID after "/approve_"
            if self.approve_trade(request_id):
                return f"✅ Trade {request_id} approved"
            else:
                return f"❌ Trade {request_id} not found or already processed"
        
        # Check for rejection command
        elif command.startswith("/reject_"):
            request_id = command[8:]  # Extract ID after "/reject_"
            if self.reject_trade(request_id):
                return f"❌ Trade {request_id} rejected"
            else:
                return f"❌ Trade {request_id} not found or already processed"
        
        # Check for status command
        elif command == "/status":
            pending = len(self.pending_requests)
            return f"📊 {pending} pending approval requests"
        
        # Not a valid command
        return None
    
    def cleanup(self):
        """Cleanup resources"""
        self.stop_thread = True
        if self.expiry_thread.is_alive():
            self.expiry_thread.join(timeout=1.0)


# Global instance
_trade_approver = None

def get_trade_approver() -> TradeApprover:
    """Get the global trade approver instance"""
    global _trade_approver
    if _trade_approver is None:
        _trade_approver = TradeApprover()
    return _trade_approver


if __name__ == "__main__":
    # Test trade approver
    from .quality_scoring import QualityScore, QualityFactor
    
    approver = get_trade_approver()
    
    # Create mock quality score
    mock_factors = {
        QualityFactor.TREND_STRENGTH: 80,
        QualityFactor.MOMENTUM: 75,
        QualityFactor.VOLUME: 60,
        QualityFactor.PATTERN_QUALITY: 70,
        QualityFactor.SESSION_QUALITY: 90,
        QualityFactor.NEWS_ALIGNMENT: 65,
        QualityFactor.MULTI_TIMEFRAME: 80,
        QualityFactor.KEY_LEVEL: 85,
        QualityFactor.RISK_REWARD: 90,
        QualityFactor.HISTORICAL_WIN_RATE: 75
    }
    
    quality_score = QualityScore(
        total_score=75,
        factors=mock_factors,
        explanation="Strong trend with good momentum",
        recommendation="buy",
        confidence=0.8,
        expected_win_rate=0.7,
        expected_risk_reward=2.5
    )
    
    # Test context
    context = {
        "regime": "TRENDING",
        "nearest_support": 1.1950,
        "nearest_resistance": 1.2050
    }
    
    # Request approval
    request = approver.request_approval(
        instrument="EUR_USD",
        side="BUY",
        entry_price=1.2000,
        stop_loss=1.1950,
        take_profit=1.2100,
        units=10000,
        quality_score=quality_score,
        context=context
    )
    
    print(f"Created approval request: {request.request_id}")
    print(f"Status: {request.status}")
    
    # Simulate approval
    if request.status == ApprovalStatus.PENDING:
        print("Approving trade...")
        approver.approve_trade(request.request_id)
        print(f"New status: {request.status}")
    
    # Simulate execution
    print("Marking as executed...")
    approver.mark_executed(
        request_id=request.request_id,
        execution_price=1.2002,
        execution_id="test_execution_001"
    )
    
    print(f"Executed: {request.executed}")
    print(f"Execution price: {request.execution_price}")
    
    # Cleanup
    approver.cleanup()
