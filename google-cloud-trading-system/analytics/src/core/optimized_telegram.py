"""
Optimized Telegram Notifier - Reduces Message Spam
Aggregates messages and sends summaries to reduce API calls
"""
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import threading
from collections import defaultdict, deque

from .telegram_notifier import TelegramNotifier

logger = logging.getLogger(__name__)

class OptimizedTelegramNotifier:
    """Optimized Telegram notifier that aggregates messages"""
    
    def __init__(self):
        self.base_notifier = TelegramNotifier()
        self.message_queue = defaultdict(list)
        self.last_sent = {}
        self.aggregation_window = 60  # seconds
        self.max_queue_size = 10
        self.rate_limit_delay = 1  # seconds between sends
        
        # Message aggregation
        self.aggregated_messages = {
            'trade_signal': [],
            'system_status': [],
            'error': []
        }
        
        # Start aggregation thread
        self.aggregation_thread = threading.Thread(target=self._aggregation_loop, daemon=True)
        self.aggregation_thread.start()
        
        logger.info("✅ OptimizedTelegramNotifier initialized with message aggregation")
    
    def send_message(self, message: str, message_type: str = 'system_status'):
        """Send message with aggregation"""
        try:
            # Add to aggregation queue
            self.aggregated_messages[message_type].append({
                'message': message,
                'timestamp': datetime.now(timezone.utc),
                'type': message_type
            })
            
            # Keep only recent messages
            if len(self.aggregated_messages[message_type]) > self.max_queue_size:
                self.aggregated_messages[message_type] = self.aggregated_messages[message_type][-self.max_queue_size:]
            
            logger.debug(f"📝 Queued {message_type} message for aggregation")
            
        except Exception as e:
            logger.error(f"❌ Error queuing message: {e}")
    
    def send_immediate(self, message: str, message_type: str = 'system_status'):
        """Send message immediately (for critical alerts)"""
        try:
            self.base_notifier.send_message(message, message_type)
            logger.info(f"📤 Sent immediate {message_type} message")
            
        except Exception as e:
            logger.error(f"❌ Error sending immediate message: {e}")
    
    def _aggregation_loop(self):
        """Main aggregation loop"""
        while True:
            try:
                time.sleep(self.aggregation_window)
                self._process_aggregated_messages()
                
            except Exception as e:
                logger.error(f"❌ Aggregation loop error: {e}")
                time.sleep(10)
    
    def _process_aggregated_messages(self):
        """Process and send aggregated messages"""
        try:
            current_time = datetime.now(timezone.utc)
            
            for message_type, messages in self.aggregated_messages.items():
                if not messages:
                    continue
                
                # Filter recent messages
                recent_messages = [
                    msg for msg in messages
                    if (current_time - msg['timestamp']).total_seconds() <= self.aggregation_window
                ]
                
                if not recent_messages:
                    continue
                
                # Create aggregated message
                aggregated_msg = self._create_aggregated_message(message_type, recent_messages)
                
                # Send aggregated message
                if aggregated_msg:
                    self.base_notifier.send_message(aggregated_msg, message_type)
                    logger.info(f"📤 Sent aggregated {message_type} message ({len(recent_messages)} items)")
                
                # Clear processed messages
                self.aggregated_messages[message_type] = []
                
                # Rate limiting
                time.sleep(self.rate_limit_delay)
                
        except Exception as e:
            logger.error(f"❌ Error processing aggregated messages: {e}")
    
    def _create_aggregated_message(self, message_type: str, messages: List[Dict[str, Any]]) -> str:
        """Create aggregated message from multiple messages"""
        try:
            if message_type == 'trade_signal':
                return self._aggregate_trade_signals(messages)
            elif message_type == 'system_status':
                return self._aggregate_system_status(messages)
            elif message_type == 'error':
                return self._aggregate_errors(messages)
            else:
                return self._aggregate_generic(messages)
                
        except Exception as e:
            logger.error(f"❌ Error creating aggregated message: {e}")
            return None
    
    def _aggregate_trade_signals(self, messages: List[Dict[str, Any]]) -> str:
        """Aggregate trade signal messages"""
        try:
            if not messages:
                return None
            
            # Count signals by strategy
            strategy_counts = defaultdict(int)
            signal_details = []
            
            for msg in messages:
                message_text = msg['message']
                if 'TRADE SIGNAL' in message_text:
                    # Extract strategy name
                    lines = message_text.split('\n')
                    strategy = 'Unknown'
                    for line in lines:
                        if 'Strategy:' in line:
                            strategy = line.split('Strategy:')[1].strip()
                            break
                    
                    strategy_counts[strategy] += 1
                    
                    # Keep first few details
                    if len(signal_details) < 3:
                        signal_details.append(message_text)
            
            # Create aggregated message
            aggregated = f"📈 TRADE SIGNALS SUMMARY ({len(messages)} signals)\n"
            aggregated += f"• Time: {datetime.now().strftime('%H:%M:%S')}\n\n"
            
            for strategy, count in strategy_counts.items():
                aggregated += f"• {strategy}: {count} signals\n"
            
            if signal_details:
                aggregated += "\n📋 Recent Signals:\n"
                for detail in signal_details:
                    aggregated += f"{detail}\n\n"
            
            return aggregated
            
        except Exception as e:
            logger.error(f"❌ Error aggregating trade signals: {e}")
            return None
    
    def _aggregate_system_status(self, messages: List[Dict[str, Any]]) -> str:
        """Aggregate system status messages"""
        try:
            if not messages:
                return None
            
            # Get latest status message
            latest_message = messages[-1]['message']
            
            # Add summary header
            aggregated = f"📊 SYSTEM STATUS SUMMARY\n"
            aggregated += f"• Time: {datetime.now().strftime('%H:%M:%S')}\n"
            aggregated += f"• Messages: {len(messages)}\n\n"
            aggregated += latest_message
            
            return aggregated
            
        except Exception as e:
            logger.error(f"❌ Error aggregating system status: {e}")
            return None
    
    def _aggregate_errors(self, messages: List[Dict[str, Any]]) -> str:
        """Aggregate error messages"""
        try:
            if not messages:
                return None
            
            # Count error types
            error_counts = defaultdict(int)
            error_details = []
            
            for msg in messages:
                message_text = msg['message']
                error_counts['Total'] += 1
                
                # Keep first few error details
                if len(error_details) < 3:
                    error_details.append(message_text)
            
            # Create aggregated message
            aggregated = f"⚠️ ERROR SUMMARY ({len(messages)} errors)\n"
            aggregated += f"• Time: {datetime.now().strftime('%H:%M:%S')}\n\n"
            
            for error_type, count in error_counts.items():
                aggregated += f"• {error_type}: {count}\n"
            
            if error_details:
                aggregated += "\n📋 Recent Errors:\n"
                for detail in error_details:
                    aggregated += f"{detail}\n\n"
            
            return aggregated
            
        except Exception as e:
            logger.error(f"❌ Error aggregating errors: {e}")
            return None
    
    def _aggregate_generic(self, messages: List[Dict[str, Any]]) -> str:
        """Aggregate generic messages"""
        try:
            if not messages:
                return None
            
            aggregated = f"📝 MESSAGE SUMMARY ({len(messages)} messages)\n"
            aggregated += f"• Time: {datetime.now().strftime('%H:%M:%S')}\n\n"
            
            # Show latest few messages
            for msg in messages[-3:]:
                aggregated += f"{msg['message']}\n\n"
            
            return aggregated
            
        except Exception as e:
            logger.error(f"❌ Error aggregating generic messages: {e}")
            return None
    
    def get_optimization_stats(self) -> Dict[str, Any]:
        """Get optimization statistics"""
        return {
            'aggregation_window': self.aggregation_window,
            'max_queue_size': self.max_queue_size,
            'rate_limit_delay': self.rate_limit_delay,
            'queued_messages': {
                msg_type: len(messages) 
                for msg_type, messages in self.aggregated_messages.items()
            }
        }

# Global instance
_optimized_notifier = None

def get_optimized_telegram() -> OptimizedTelegramNotifier:
    """Get optimized Telegram notifier instance"""
    global _optimized_notifier
    if _optimized_notifier is None:
        _optimized_notifier = OptimizedTelegramNotifier()
    return _optimized_notifier
