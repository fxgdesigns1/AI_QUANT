#!/usr/bin/env python3
"""
Hybrid Execution System
Combines automated execution with manual approval workflow
"""

import os
import sys
import yaml
import logging
import time
from datetime import datetime
import pytz
import json
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load credentials
try:
    with open('app.yaml') as f:
        config = yaml.safe_load(f)
        os.environ['OANDA_API_KEY'] = config['env_variables']['OANDA_API_KEY']
    with open('accounts.yaml') as f:
        accounts = yaml.safe_load(f)
        os.environ['OANDA_ACCOUNT_ID'] = accounts['accounts'][0]['id']
    os.environ['TELEGRAM_TOKEN'] = "${TELEGRAM_TOKEN}"
    os.environ['TELEGRAM_CHAT_ID'] = "${TELEGRAM_CHAT_ID}"
    logger.info("✅ Credentials loaded")
except Exception as e:
    logger.error(f"❌ Failed to load credentials: {e}")
    sys.exit(1)

# Import core modules
from src.core.oanda_client import OandaClient
from src.core.telegram_notifier import TelegramNotifier

# Import contextual modules
try:
    from src.core.session_manager import get_session_manager
    from src.core.price_context_analyzer import get_price_context_analyzer
    from src.core.quality_scoring import get_quality_scoring, QualityFactor
    from src.core.historical_news_fetcher import get_historical_news_fetcher
    from src.core.trade_approver import get_trade_approver, ApprovalStatus
    logger.info("✅ Contextual modules imported")
except Exception as e:
    logger.error(f"❌ Failed to import contextual modules: {e}")
    sys.exit(1)

# Import strategy modules
from morning_scanner import scan_for_opportunities


class ExecutionMode(Enum):
    """Execution modes for the hybrid system"""
    FULLY_AUTOMATED = "fully_automated"  # Execute all trades automatically
    QUALITY_BASED = "quality_based"      # Auto-execute high quality, manual for medium
    FULLY_MANUAL = "fully_manual"        # All trades require manual approval


class HybridExecutionSystem:
    """
    Hybrid Execution System
    
    Combines automated execution with manual approval workflow
    based on trade quality and user preferences
    """
    
    def __init__(self, mode: ExecutionMode = ExecutionMode.QUALITY_BASED,
                auto_threshold: int = 80, risk_per_trade: float = 0.01):
        """
        Initialize the hybrid execution system
        
        Args:
            mode: Execution mode (fully_automated, quality_based, fully_manual)
            auto_threshold: Quality threshold for automatic execution (0-100)
            risk_per_trade: Risk per trade as percentage of account balance (0.01 = 1%)
        """
        self.mode = mode
        self.auto_threshold = auto_threshold
        self.risk_per_trade = risk_per_trade
        
        # Initialize core components
        self.client = OandaClient(
            os.environ['OANDA_API_KEY'],
            os.environ['OANDA_ACCOUNT_ID'],
            'practice'
        )
        self.notifier = TelegramNotifier()
        self.trade_approver = get_trade_approver()
        self.quality_scorer = get_quality_scoring()
        self.session_manager = get_session_manager()
        
        # Track open trades
        self.open_trades = {}
        self.pending_approvals = {}
        
        logger.info(f"✅ Hybrid Execution System initialized in {mode.value} mode")
        logger.info(f"   Auto-execution threshold: {auto_threshold}/100")
        logger.info(f"   Risk per trade: {risk_per_trade*100:.1f}%")
    
    def scan_and_execute(self) -> Dict[str, Any]:
        """
        Scan for opportunities and execute based on mode
        
        Returns:
            Dict with execution results
        """
        logger.info("🔍 Scanning for trading opportunities...")
        
        # Get account info for position sizing
        account_info = self.client.get_account_info()
        balance = account_info.balance
        
        # Scan for opportunities
        opportunities = scan_for_opportunities()
        
        if not opportunities:
            logger.info("❌ No quality opportunities found")
            return {"status": "no_opportunities", "count": 0}
        
        logger.info(f"✅ Found {len(opportunities)} opportunities")
        
        # Process each opportunity based on mode
        auto_executed = []
        manual_approval = []
        skipped = []
        
        for opp in opportunities:
            try:
                instrument = opp['instrument']
                direction = opp['direction']
                entry = opp['entry']
                stop_loss = opp['stop_loss']
                take_profit = opp['take_profit']
                quality = opp['quality']
                
                # Calculate position size
                sl_distance = abs(entry - stop_loss)
                dollar_risk = balance * self.risk_per_trade
                
                # For Gold (XAU_USD): 1 unit = 1 troy ounce
                # For Forex: 1 unit = 1 unit of base currency
                if instrument == 'XAU_USD':
                    units = int(dollar_risk / sl_distance)
                else:
                    # Forex pairs: risk in pips, need to adjust
                    # Assuming 0.0001 pip value for most pairs, 0.01 for JPY pairs
                    pip_value = 10 if 'JPY' in instrument else 10000
                    units = int((dollar_risk / sl_distance) * pip_value)
                
                # Adjust units direction based on trade direction
                if direction == "SELL":
                    units = -units
                
                # Determine execution path based on mode and quality
                if self.mode == ExecutionMode.FULLY_AUTOMATED:
                    # Execute automatically regardless of quality
                    self._execute_trade(instrument, units, entry, stop_loss, take_profit)
                    auto_executed.append(opp)
                    
                elif self.mode == ExecutionMode.QUALITY_BASED:
                    # Execute automatically if quality is above threshold
                    if quality >= self.auto_threshold:
                        self._execute_trade(instrument, units, entry, stop_loss, take_profit)
                        auto_executed.append(opp)
                    else:
                        # Request manual approval for lower quality trades
                        self._request_approval(opp, units)
                        manual_approval.append(opp)
                
                elif self.mode == ExecutionMode.FULLY_MANUAL:
                    # All trades require manual approval
                    self._request_approval(opp, units)
                    manual_approval.append(opp)
                
            except Exception as e:
                logger.error(f"❌ Error processing opportunity {opp['instrument']}: {e}")
                skipped.append(opp)
        
        # Send summary notification
        self._send_execution_summary(auto_executed, manual_approval, skipped)
        
        return {
            "status": "success",
            "auto_executed": len(auto_executed),
            "manual_approval": len(manual_approval),
            "skipped": len(skipped),
            "total": len(opportunities)
        }
    
    def _execute_trade(self, instrument: str, units: int, 
                      entry_price: float, stop_loss: float, take_profit: float) -> bool:
        """
        Execute trade automatically
        
        Args:
            instrument: Instrument to trade
            units: Number of units (positive for buy, negative for sell)
            entry_price: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit price
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"🔄 Executing trade: {instrument} {units} units")
            
            # Place market order with stop loss and take profit
            result = self.client.place_market_order(
                instrument=instrument,
                units=units,
                stop_loss=stop_loss,
                take_profit=take_profit
            )
            
            if result and 'orderFillTransaction' in result:
                trade_id = result['orderFillTransaction']['id']
                filled_price = float(result['orderFillTransaction']['price'])
                
                logger.info(f"✅ Trade executed: {instrument} {units} units @ {filled_price}")
                logger.info(f"   Trade ID: {trade_id}")
                logger.info(f"   SL: {stop_loss} | TP: {take_profit}")
                
                # Track open trade
                self.open_trades[trade_id] = {
                    'instrument': instrument,
                    'units': units,
                    'entry_price': filled_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'time': datetime.now(pytz.UTC).isoformat()
                }
                
                # Save open trades to file
                self._save_open_trades()
                
                return True
            else:
                logger.error(f"❌ Failed to execute trade: {result}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error executing trade: {e}")
            return False
    
    def _request_approval(self, opportunity: Dict[str, Any], units: int) -> bool:
        """
        Request manual approval for trade
        
        Args:
            opportunity: Trading opportunity
            units: Number of units to trade
            
        Returns:
            True if request sent, False otherwise
        """
        try:
            instrument = opportunity['instrument']
            direction = opportunity['direction']
            entry = opportunity['entry']
            stop_loss = opportunity['stop_loss']
            take_profit = opportunity['take_profit']
            quality = opportunity['quality']
            
            logger.info(f"📝 Requesting approval: {instrument} {direction} ({quality}/100)")
            
            # Get context for approval request
            context = {}
            if 'overall_trend' in opportunity:
                context['overall_trend'] = opportunity['overall_trend']
            if 'nearest_support' in opportunity:
                context['nearest_support'] = opportunity['nearest_support']
            if 'nearest_resistance' in opportunity:
                context['nearest_resistance'] = opportunity['nearest_resistance']
            
            # Request approval
            request = self.trade_approver.request_approval(
                instrument=instrument,
                side=direction,
                entry_price=entry,
                stop_loss=stop_loss,
                take_profit=take_profit,
                units=units,
                quality_score=opportunity.get('quality_score'),  # May be None
                context=context
            )
            
            # Track pending approval
            self.pending_approvals[request.request_id] = {
                'request': request,
                'opportunity': opportunity,
                'units': units
            }
            
            logger.info(f"✅ Approval requested: {request.request_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error requesting approval: {e}")
            return False
    
    def _send_execution_summary(self, auto_executed: List[Dict], 
                               manual_approval: List[Dict],
                               skipped: List[Dict]) -> None:
        """Send execution summary notification"""
        try:
            now = datetime.now(pytz.timezone('Europe/London'))
            
            message = f"""🤖 **HYBRID EXECUTION SUMMARY - {now.strftime('%H:%M')}**

**Mode:** {self.mode.value.replace('_', ' ').title()}
**Auto Threshold:** {self.auto_threshold}/100

**Results:**
- Auto-executed: {len(auto_executed)} trades
- Manual approval: {len(manual_approval)} trades
- Skipped: {len(skipped)} trades

"""
            
            if auto_executed:
                message += "**Auto-Executed Trades:**\n"
                for i, trade in enumerate(auto_executed[:5], 1):  # Show top 5
                    message += f"{i}. {trade['instrument']} {trade['direction']} (Quality: {trade['quality']}/100)\n"
                if len(auto_executed) > 5:
                    message += f"... and {len(auto_executed) - 5} more\n"
                message += "\n"
            
            if manual_approval:
                message += "**Pending Approval:**\n"
                for i, trade in enumerate(manual_approval[:5], 1):  # Show top 5
                    message += f"{i}. {trade['instrument']} {trade['direction']} (Quality: {trade['quality']}/100)\n"
                if len(manual_approval) > 5:
                    message += f"... and {len(manual_approval) - 5} more\n"
                message += "\nUse Telegram commands to approve/reject trades.\n"
            
            self.notifier.send_system_status("Hybrid Execution Summary", message)
            logger.info("✅ Execution summary sent")
            
        except Exception as e:
            logger.error(f"❌ Error sending execution summary: {e}")
    
    def _save_open_trades(self) -> None:
        """Save open trades to file"""
        try:
            with open('open_trades.json', 'w') as f:
                json.dump(self.open_trades, f, indent=2, default=str)
            logger.info("✅ Open trades saved")
        except Exception as e:
            logger.error(f"❌ Error saving open trades: {e}")
    
    def _load_open_trades(self) -> None:
        """Load open trades from file"""
        try:
            if os.path.exists('open_trades.json'):
                with open('open_trades.json', 'r') as f:
                    self.open_trades = json.load(f)
                logger.info(f"✅ Loaded {len(self.open_trades)} open trades")
        except Exception as e:
            logger.error(f"❌ Error loading open trades: {e}")
    
    def process_approval_commands(self) -> Dict[str, Any]:
        """
        Process approval commands from Telegram
        
        Returns:
            Dict with processing results
        """
        logger.info("📱 Processing approval commands...")
        
        # Get pending commands - use get_pending_requests and simulate commands
        # This is a temporary workaround until the trade_approver has get_pending_commands
        pending_requests = self.trade_approver.get_pending_requests()
        commands = []
        
        # No commands for now, just a placeholder
        # In a real implementation, we would check for new Telegram messages
        # and extract commands from them
        
        if not commands:
            logger.info("✅ No pending commands")
            return {"status": "no_commands", "count": 0}
        
        logger.info(f"✅ Found {len(commands)} pending commands")
        
        # Process each command
        approved = []
        rejected = []
        invalid = []
        
        for command in commands:
            try:
                cmd_type, request_id = command
                
                if request_id not in self.pending_approvals:
                    logger.warning(f"⚠️ Invalid request ID: {request_id}")
                    invalid.append(command)
                    continue
                
                pending = self.pending_approvals[request_id]
                request = pending['request']
                opportunity = pending['opportunity']
                units = pending['units']
                
                if cmd_type == 'approve':
                    # Approve and execute trade
                    logger.info(f"✅ Approving trade: {request_id}")
                    self.trade_approver.approve_trade(request_id)
                    
                    # Execute the approved trade
                    success = self._execute_trade(
                        instrument=opportunity['instrument'],
                        units=units,
                        entry_price=opportunity['entry'],
                        stop_loss=opportunity['stop_loss'],
                        take_profit=opportunity['take_profit']
                    )
                    
                    if success:
                        # Mark as executed in approver
                        self.trade_approver.mark_executed(
                            request_id=request_id,
                            execution_price=opportunity['entry'],
                            execution_id=f"manual_{int(time.time())}"
                        )
                        approved.append(command)
                    else:
                        # Execution failed
                        self.trade_approver.reject_trade(request_id, reason="Execution failed")
                        rejected.append(command)
                
                elif cmd_type == 'reject':
                    # Reject trade
                    logger.info(f"❌ Rejecting trade: {request_id}")
                    self.trade_approver.reject_trade(request_id, reason="User rejected")
                    rejected.append(command)
                
                else:
                    # Invalid command
                    logger.warning(f"⚠️ Invalid command: {cmd_type}")
                    invalid.append(command)
            
            except Exception as e:
                logger.error(f"❌ Error processing command: {e}")
                invalid.append(command)
        
        # Remove processed commands
        for command in approved + rejected:
            _, request_id = command
            if request_id in self.pending_approvals:
                del self.pending_approvals[request_id]
        
        # Send summary notification
        if approved or rejected:
            self._send_command_summary(approved, rejected, invalid)
        
        return {
            "status": "success",
            "approved": len(approved),
            "rejected": len(rejected),
            "invalid": len(invalid),
            "total": len(commands)
        }
    
    def _send_command_summary(self, approved: List[Tuple], 
                             rejected: List[Tuple],
                             invalid: List[Tuple]) -> None:
        """Send command processing summary notification"""
        try:
            now = datetime.now(pytz.timezone('Europe/London'))
            
            message = f"""📱 **APPROVAL PROCESSING - {now.strftime('%H:%M')}**

**Results:**
- Approved & Executed: {len(approved)} trades
- Rejected: {len(rejected)} trades
- Invalid commands: {len(invalid)}

"""
            
            if approved:
                message += "**Approved Trades:**\n"
                for i, (_, request_id) in enumerate(approved[:5], 1):  # Show top 5
                    if request_id in self.pending_approvals:
                        opp = self.pending_approvals[request_id]['opportunity']
                        message += f"{i}. {opp['instrument']} {opp['direction']} (Quality: {opp['quality']}/100)\n"
                if len(approved) > 5:
                    message += f"... and {len(approved) - 5} more\n"
                message += "\n"
            
            if rejected:
                message += "**Rejected Trades:**\n"
                for i, (_, request_id) in enumerate(rejected[:5], 1):  # Show top 5
                    if request_id in self.pending_approvals:
                        opp = self.pending_approvals[request_id]['opportunity']
                        message += f"{i}. {opp['instrument']} {opp['direction']} (Quality: {opp['quality']}/100)\n"
                if len(rejected) > 5:
                    message += f"... and {len(rejected) - 5} more\n"
            
            self.notifier.send_system_status("Approval Processing Summary", message)
            logger.info("✅ Command summary sent")
            
        except Exception as e:
            logger.error(f"❌ Error sending command summary: {e}")
    
    def update_open_trades(self) -> Dict[str, Any]:
        """
        Update and manage open trades
        
        Returns:
            Dict with update results
        """
        logger.info("🔄 Updating open trades...")
        
        # Load open trades
        self._load_open_trades()
        
        if not self.open_trades:
            logger.info("✅ No open trades to update")
            return {"status": "no_trades", "count": 0}
        
        logger.info(f"✅ Updating {len(self.open_trades)} open trades")
        
        # Get current positions
        positions = self.client.get_positions()
        
        # Build position map for quick lookup
        position_map = {}
        for position in positions:
            instrument = position.get('instrument')
            position_map[instrument] = position
        
        # Update each open trade
        closed_trades = []
        updated_trades = []
        
        for trade_id, trade in list(self.open_trades.items()):
            try:
                instrument = trade['instrument']
                
                # Check if position still exists
                if instrument not in position_map:
                    logger.info(f"🏁 Trade closed: {instrument}")
                    closed_trades.append(trade)
                    del self.open_trades[trade_id]
                    continue
                
                # Update trade with current position info
                position = position_map[instrument]
                
                # Determine if long or short
                units = trade['units']
                if units > 0:
                    # Long position
                    unrealized_pl = float(position.get('long', {}).get('unrealizedPL', 0))
                    current_price = float(position.get('long', {}).get('averagePrice', 0))
                else:
                    # Short position
                    unrealized_pl = float(position.get('short', {}).get('unrealizedPL', 0))
                    current_price = float(position.get('short', {}).get('averagePrice', 0))
                
                # Update trade info
                trade['unrealized_pl'] = unrealized_pl
                trade['current_price'] = current_price
                trade['last_updated'] = datetime.now(pytz.UTC).isoformat()
                
                updated_trades.append(trade)
                
            except Exception as e:
                logger.error(f"❌ Error updating trade {trade_id}: {e}")
        
        # Save updated open trades
        self._save_open_trades()
        
        # Send update notification if there are changes
        if closed_trades:
            self._send_trade_update(updated_trades, closed_trades)
        
        return {
            "status": "success",
            "updated": len(updated_trades),
            "closed": len(closed_trades),
            "total": len(self.open_trades) + len(closed_trades)
        }
    
    def _send_trade_update(self, updated_trades: List[Dict], 
                          closed_trades: List[Dict]) -> None:
        """Send trade update notification"""
        try:
            now = datetime.now(pytz.timezone('Europe/London'))
            
            message = f"""📊 **TRADE UPDATE - {now.strftime('%H:%M')}**

**Open Positions:** {len(updated_trades)}
**Recently Closed:** {len(closed_trades)}

"""
            
            if updated_trades:
                message += "**Open Positions:**\n"
                for i, trade in enumerate(updated_trades[:5], 1):  # Show top 5
                    direction = "LONG" if trade['units'] > 0 else "SHORT"
                    pl = trade.get('unrealized_pl', 0)
                    pl_emoji = "✅" if pl > 0 else "❌"
                    
                    message += f"{i}. {trade['instrument']} {direction}: {pl_emoji} ${pl:.2f}\n"
                if len(updated_trades) > 5:
                    message += f"... and {len(updated_trades) - 5} more\n"
                message += "\n"
            
            if closed_trades:
                message += "**Recently Closed:**\n"
                for i, trade in enumerate(closed_trades[:5], 1):  # Show top 5
                    direction = "LONG" if trade['units'] > 0 else "SHORT"
                    message += f"{i}. {trade['instrument']} {direction}\n"
                if len(closed_trades) > 5:
                    message += f"... and {len(closed_trades) - 5} more\n"
            
            self.notifier.send_system_status("Trade Update", message)
            logger.info("✅ Trade update sent")
            
        except Exception as e:
            logger.error(f"❌ Error sending trade update: {e}")


def run_hybrid_system(mode_str: str = "quality_based", 
                     auto_threshold: int = 80,
                     risk_per_trade: float = 0.01) -> Dict[str, Any]:
    """
    Run the hybrid execution system
    
    Args:
        mode_str: Execution mode (fully_automated, quality_based, fully_manual)
        auto_threshold: Quality threshold for automatic execution (0-100)
        risk_per_trade: Risk per trade as percentage of account balance (0.01 = 1%)
        
    Returns:
        Dict with execution results
    """
    # Convert mode string to enum
    mode_map = {
        "fully_automated": ExecutionMode.FULLY_AUTOMATED,
        "quality_based": ExecutionMode.QUALITY_BASED,
        "fully_manual": ExecutionMode.FULLY_MANUAL
    }
    
    mode = mode_map.get(mode_str, ExecutionMode.QUALITY_BASED)
    
    # Initialize system
    system = HybridExecutionSystem(
        mode=mode,
        auto_threshold=auto_threshold,
        risk_per_trade=risk_per_trade
    )
    
    # Scan and execute
    execution_results = system.scan_and_execute()
    
    # Process approval commands
    command_results = system.process_approval_commands()
    
    # Update open trades
    update_results = system.update_open_trades()
    
    # Return combined results
    return {
        "execution": execution_results,
        "commands": command_results,
        "updates": update_results,
        "timestamp": datetime.now(pytz.UTC).isoformat()
    }


if __name__ == "__main__":
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Hybrid Execution System")
    parser.add_argument("--mode", default="quality_based", 
                       choices=["fully_automated", "quality_based", "fully_manual"],
                       help="Execution mode")
    parser.add_argument("--threshold", type=int, default=80,
                       help="Quality threshold for automatic execution (0-100)")
    parser.add_argument("--risk", type=float, default=0.01,
                       help="Risk per trade as percentage of account balance (0.01 = 1%)")
    args = parser.parse_args()
    
    # Run the system
    results = run_hybrid_system(
        mode_str=args.mode,
        auto_threshold=args.threshold,
        risk_per_trade=args.risk
    )
    
    # Print results
    logger.info("\n" + "="*80)
    logger.info("HYBRID EXECUTION SYSTEM RESULTS")
    logger.info("="*80)
    
    logger.info(f"\nExecution Results:")
    logger.info(f"  Status: {results['execution']['status']}")
    logger.info(f"  Auto-executed: {results['execution'].get('auto_executed', 0)} trades")
    logger.info(f"  Manual approval: {results['execution'].get('manual_approval', 0)} trades")
    logger.info(f"  Skipped: {results['execution'].get('skipped', 0)} trades")
    
    logger.info(f"\nCommand Processing:")
    logger.info(f"  Status: {results['commands']['status']}")
    logger.info(f"  Approved: {results['commands'].get('approved', 0)} trades")
    logger.info(f"  Rejected: {results['commands'].get('rejected', 0)} trades")
    logger.info(f"  Invalid: {results['commands'].get('invalid', 0)} commands")
    
    logger.info(f"\nTrade Updates:")
    logger.info(f"  Status: {results['updates']['status']}")
    logger.info(f"  Updated: {results['updates'].get('updated', 0)} trades")
    logger.info(f"  Closed: {results['updates'].get('closed', 0)} trades")
    
    logger.info("\n" + "="*80)
