#!/usr/bin/env python3
"""
Adaptive Trading System
Intelligent system that learns from market patterns and automatically adapts strategies
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import threading
import time
from enum import Enum

from .oanda_client import OandaClient
from .telegram_notifier import TelegramNotifier

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MarketCondition(Enum):
    """Market condition states"""
    NORMAL = "normal"
    ELEVATED_VOLATILITY = "elevated_volatility"
    HIGH_VOLATILITY = "high_volatility"
    CENTRAL_BANK_EVENT = "central_bank_event"
    MOMENTUM_REVERSAL = "momentum_reversal"
    RISK_OFF = "risk_off"

class AdaptationLevel(Enum):
    """Adaptation intensity levels"""
    NONE = "none"
    LIGHT = "light"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"

@dataclass
class MarketSignal:
    """Market signal data"""
    timestamp: datetime
    signal_type: str
    instrument: str
    value: float
    threshold: float
    condition: MarketCondition
    confidence: float

@dataclass
class AdaptationRule:
    """Adaptation rule definition"""
    condition: MarketCondition
    trigger_threshold: float
    action: str
    parameters: Dict[str, Any]
    description: str
    priority: int = 1

@dataclass
class RiskParameters:
    """Dynamic risk parameters"""
    position_size_multiplier: float = 1.0
    stop_loss_adjustment: float = 1.0
    take_profit_adjustment: float = 1.0
    max_positions: int = 5
    trade_frequency: str = "normal"
    max_margin_usage: float = 0.8
    adaptation_level: AdaptationLevel = AdaptationLevel.NONE

class AdaptiveMarketDetector:
    """Detects market conditions that require strategy adaptations"""
    
    def __init__(self):
        self.market_signals: List[MarketSignal] = []
        self.current_conditions: Dict[str, MarketCondition] = {}
        self.price_history: Dict[str, List[float]] = {}
        self.volatility_history: Dict[str, List[float]] = {}
        
        # Thresholds for condition detection
        self.thresholds = {
            'high_volatility': 0.02,  # 2% price change
            'elevated_volatility': 0.01,  # 1% price change
            'spread_widening': 0.5,  # 50% spread increase
            'margin_usage_critical': 0.8,  # 80% margin usage
            'momentum_reversal': 0.015,  # 1.5% reversal
            'correlation_break': 0.3  # 30% correlation change
        }
        
        logger.info("🧠 Adaptive Market Detector initialized")
    
    def add_price_data(self, instrument: str, price: float, timestamp: datetime = None):
        """Add price data for analysis"""
        if timestamp is None:
            timestamp = datetime.now()
        
        if instrument not in self.price_history:
            self.price_history[instrument] = []
        
        self.price_history[instrument].append(price)
        
        # Keep only last 100 prices for efficiency
        if len(self.price_history[instrument]) > 100:
            self.price_history[instrument] = self.price_history[instrument][-100:]
        
        # Calculate volatility
        self._update_volatility(instrument)
        
        # Check for signals
        self._check_price_signals(instrument, price, timestamp)
    
    def _update_volatility(self, instrument: str):
        """Update volatility calculations"""
        prices = self.price_history[instrument]
        if len(prices) < 10:
            return
        
        # Calculate recent volatility (last 10 prices)
        recent_prices = prices[-10:]
        volatility = 0.0
        
        for i in range(1, len(recent_prices)):
            change = abs(recent_prices[i] - recent_prices[i-1]) / recent_prices[i-1]
            volatility += change
        
        volatility /= (len(recent_prices) - 1)
        
        if instrument not in self.volatility_history:
            self.volatility_history[instrument] = []
        
        self.volatility_history[instrument].append(volatility)
        
        # Keep only last 50 volatility readings
        if len(self.volatility_history[instrument]) > 50:
            self.volatility_history[instrument] = self.volatility_history[instrument][-50:]
    
    def _check_price_signals(self, instrument: str, price: float, timestamp: datetime):
        """Check for price-based signals"""
        prices = self.price_history[instrument]
        
        if len(prices) < 2:
            return
        
        # Check for high volatility
        recent_change = abs(price - prices[-2]) / prices[-2]
        
        if recent_change >= self.thresholds['high_volatility']:
            signal = MarketSignal(
                timestamp=timestamp,
                signal_type="high_volatility",
                instrument=instrument,
                value=recent_change,
                threshold=self.thresholds['high_volatility'],
                condition=MarketCondition.HIGH_VOLATILITY,
                confidence=min(recent_change / self.thresholds['high_volatility'], 2.0)
            )
            self.market_signals.append(signal)
            self.current_conditions[instrument] = MarketCondition.HIGH_VOLATILITY
            
        elif recent_change >= self.thresholds['elevated_volatility']:
            signal = MarketSignal(
                timestamp=timestamp,
                signal_type="elevated_volatility",
                instrument=instrument,
                value=recent_change,
                threshold=self.thresholds['elevated_volatility'],
                condition=MarketCondition.ELEVATED_VOLATILITY,
                confidence=min(recent_change / self.thresholds['elevated_volatility'], 1.5)
            )
            self.market_signals.append(signal)
            if instrument not in self.current_conditions:
                self.current_conditions[instrument] = MarketCondition.ELEVATED_VOLATILITY
    
    def check_margin_signals(self, account_info) -> List[MarketSignal]:
        """Check for margin-based signals"""
        signals = []
        margin_usage = account_info.margin_used / account_info.balance if account_info.balance > 0 else 0
        
        if margin_usage >= self.thresholds['margin_usage_critical']:
            signal = MarketSignal(
                timestamp=datetime.now(),
                signal_type="high_margin_usage",
                instrument="PORTFOLIO",
                value=margin_usage,
                threshold=self.thresholds['margin_usage_critical'],
                condition=MarketCondition.HIGH_VOLATILITY,
                confidence=min(margin_usage / self.thresholds['margin_usage_critical'], 2.0)
            )
            signals.append(signal)
        
        return signals
    
    def get_current_market_condition(self) -> MarketCondition:
        """Get overall market condition"""
        if not self.current_conditions:
            return MarketCondition.NORMAL
        
        # Return the most severe condition
        severity_order = {
            MarketCondition.NORMAL: 0,
            MarketCondition.ELEVATED_VOLATILITY: 1,
            MarketCondition.HIGH_VOLATILITY: 2,
            MarketCondition.CENTRAL_BANK_EVENT: 3,
            MarketCondition.MOMENTUM_REVERSAL: 4,
            MarketCondition.RISK_OFF: 5
        }
        
        max_severity = max(severity_order[condition] for condition in self.current_conditions.values())
        
        for condition, severity in severity_order.items():
            if severity == max_severity:
                return condition
        
        return MarketCondition.NORMAL

class AdaptiveRiskManager:
    """Manages dynamic risk parameters based on market conditions"""
    
    def __init__(self):
        self.base_risk_parameters = {
            'PRIMARY': RiskParameters(
                position_size_multiplier=1.0,
                stop_loss_adjustment=1.0,
                max_positions=5,
                max_margin_usage=0.8
            ),
            'GOLD': RiskParameters(
                position_size_multiplier=1.0,
                stop_loss_adjustment=1.0,
                max_positions=3,
                max_margin_usage=0.6
            ),
            'ALPHA': RiskParameters(
                position_size_multiplier=1.0,
                stop_loss_adjustment=1.0,
                max_positions=7,
                max_margin_usage=0.8
            )
        }
        
        self.current_risk_parameters = self.base_risk_parameters.copy()
        self.adaptation_rules = self._create_adaptation_rules()
        
        logger.info("🛡️ Adaptive Risk Manager initialized")
    
    def _create_adaptation_rules(self) -> List[AdaptationRule]:
        """Create adaptation rules based on learned patterns"""
        return [
            AdaptationRule(
                condition=MarketCondition.HIGH_VOLATILITY,
                trigger_threshold=0.02,
                action="reduce_position_sizes",
                parameters={'reduction_factor': 0.5, 'max_margin_usage': 0.6},
                description="Reduce position sizes by 50% during high volatility",
                priority=1
            ),
            AdaptationRule(
                condition=MarketCondition.ELEVATED_VOLATILITY,
                trigger_threshold=0.01,
                action="moderate_reduction",
                parameters={'reduction_factor': 0.75, 'max_margin_usage': 0.7},
                description="Moderate position size reduction during elevated volatility",
                priority=2
            ),
            AdaptationRule(
                condition=MarketCondition.CENTRAL_BANK_EVENT,
                trigger_threshold=1.0,
                action="pause_trading",
                parameters={'pause_duration_hours': 4, 'monitor_volatility': True},
                description="Pause new trades during central bank events",
                priority=1
            ),
            AdaptationRule(
                condition=MarketCondition.MOMENTUM_REVERSAL,
                trigger_threshold=0.015,
                action="close_opposite_positions",
                parameters={'close_percentage': 0.3, 'adjust_stops': True},
                description="Close 30% of opposite positions during momentum reversals",
                priority=1
            )
        ]
    
    def adapt_risk_parameters(self, market_condition: MarketCondition, 
                            account_name: str, account_info) -> RiskParameters:
        """Adapt risk parameters based on market conditions"""
        base_params = self.base_risk_parameters[account_name]
        adapted_params = RiskParameters(
            position_size_multiplier=base_params.position_size_multiplier,
            stop_loss_adjustment=base_params.stop_loss_adjustment,
            take_profit_adjustment=base_params.take_profit_adjustment,
            max_positions=base_params.max_positions,
            trade_frequency=base_params.trade_frequency,
            max_margin_usage=base_params.max_margin_usage
        )
        
        # Apply adaptations based on market condition
        for rule in self.adaptation_rules:
            if rule.condition == market_condition:
                if rule.action == "reduce_position_sizes":
                    adapted_params.position_size_multiplier *= rule.parameters['reduction_factor']
                    adapted_params.max_margin_usage = rule.parameters['max_margin_usage']
                    adapted_params.adaptation_level = AdaptationLevel.AGGRESSIVE
                    
                elif rule.action == "moderate_reduction":
                    adapted_params.position_size_multiplier *= rule.parameters['reduction_factor']
                    adapted_params.max_margin_usage = rule.parameters['max_margin_usage']
                    adapted_params.adaptation_level = AdaptationLevel.MODERATE
                    
                elif rule.action == "pause_trading":
                    adapted_params.trade_frequency = "paused"
                    adapted_params.adaptation_level = AdaptationLevel.AGGRESSIVE
                    
                elif rule.action == "close_opposite_positions":
                    adapted_params.adaptation_level = AdaptationLevel.MODERATE
        
        # Account-specific adaptations
        if account_name == "GOLD" and market_condition == MarketCondition.HIGH_VOLATILITY:
            # Gold scalping needs extra protection during high volatility
            adapted_params.position_size_multiplier *= 0.5
            adapted_params.stop_loss_adjustment *= 1.5
            adapted_params.max_positions = 2
        
        elif account_name == "ALPHA" and market_condition == MarketCondition.MOMENTUM_REVERSAL:
            # Momentum strategy needs faster adaptation
            adapted_params.position_size_multiplier *= 0.3
            adapted_params.stop_loss_adjustment *= 0.8
        
        self.current_risk_parameters[account_name] = adapted_params
        return adapted_params

class AdaptiveTradingSystem:
    """Main adaptive trading system that orchestrates all components"""
    
    def __init__(self, oanda_clients: Dict[str, OandaClient], telegram_notifier: TelegramNotifier = None):
        self.oanda_clients = oanda_clients
        self.telegram_notifier = telegram_notifier
        self.market_detector = AdaptiveMarketDetector()
        self.risk_manager = AdaptiveRiskManager()
        
        # System state
        self.is_running = False
        self.monitoring_thread = None
        self.last_adaptation_time = {}
        self.adaptation_cooldown = 300  # 5 minutes between adaptations
        
        # Instruments to monitor
        self.monitored_instruments = [
            'EUR_USD', 'GBP_USD', 'USD_JPY', 'XAU_USD',
            'AUD_USD', 'USD_CAD', 'NZD_USD', 'USD_CHF'
        ]
        
        logger.info("🤖 Adaptive Trading System initialized")
    
    def start_monitoring(self):
        """Start the adaptive monitoring system"""
        if self.is_running:
            logger.warning("Adaptive system already running")
            return
        
        self.is_running = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        logger.info("🚀 Adaptive monitoring started")
        
        if self.telegram_notifier:
            self.telegram_notifier.send_message(
                "🤖 Adaptive Trading System Started\n"
                "📊 Monitoring market conditions for automatic adaptations"
            )
    
    def stop_monitoring(self):
        """Stop the adaptive monitoring system"""
        self.is_running = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        
        logger.info("🛑 Adaptive monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.is_running:
            try:
                self._check_market_conditions()
                self._apply_adaptations()
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"❌ Error in monitoring loop: {e}")
                time.sleep(60)  # Wait longer on error
    
    def _check_market_conditions(self):
        """Check current market conditions"""
        try:
            # Get current prices for all monitored instruments
            for instrument in self.monitored_instruments:
                try:
                    prices = list(self.oanda_clients.values())[0].get_current_prices([instrument])
                    if instrument in prices:
                        mid_price = (prices[instrument].bid + prices[instrument].ask) / 2
                        self.market_detector.add_price_data(instrument, mid_price)
                except Exception as e:
                    logger.warning(f"Failed to get price for {instrument}: {e}")
            
            # Check account-specific signals
            for account_name, client in self.oanda_clients.items():
                try:
                    account_info = client.get_account_info()
                    margin_signals = self.market_detector.check_margin_signals(account_info)
                    
                    for signal in margin_signals:
                        self.market_detector.market_signals.append(signal)
                        
                except Exception as e:
                    logger.warning(f"Failed to check account {account_name}: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Error checking market conditions: {e}")
    
    def _apply_adaptations(self):
        """Apply adaptations based on detected conditions"""
        current_condition = self.market_detector.get_current_market_condition()
        
        if current_condition == MarketCondition.NORMAL:
            return
        
        for account_name, client in self.oanda_clients.items():
            # Check cooldown
            if (account_name in self.last_adaptation_time and 
                time.time() - self.last_adaptation_time[account_name] < self.adaptation_cooldown):
                continue
            
            try:
                account_info = client.get_account_info()
                adapted_params = self.risk_manager.adapt_risk_parameters(
                    current_condition, account_name, account_info
                )
                
                # Apply adaptations
                self._execute_adaptations(account_name, client, adapted_params, current_condition)
                
                self.last_adaptation_time[account_name] = time.time()
                
                # Send notification
                if self.telegram_notifier:
                    self._send_adaptation_notification(
                        account_name, current_condition, adapted_params
                    )
                    
            except Exception as e:
                logger.error(f"❌ Failed to apply adaptations for {account_name}: {e}")
    
    def _execute_adaptations(self, account_name: str, client: OandaClient, 
                           adapted_params: RiskParameters, condition: MarketCondition):
        """Execute specific adaptations"""
        
        if adapted_params.trade_frequency == "paused":
            logger.info(f"⏸️ Pausing trades for {account_name} due to {condition.value}")
            return
        
        # Check if position size reduction is needed
        if adapted_params.position_size_multiplier < 1.0:
            logger.info(f"📉 Reducing position sizes for {account_name} by "
                       f"{int((1 - adapted_params.position_size_multiplier) * 100)}%")
        
        # Check if margin usage is too high
        account_info = client.get_account_info()
        current_margin_usage = account_info.margin_used / account_info.balance if account_info.balance > 0 else 0
        
        if current_margin_usage > adapted_params.max_margin_usage:
            logger.warning(f"⚠️ High margin usage detected for {account_name}: "
                          f"{current_margin_usage:.1%}")
            
            # Close some positions if margin usage is critical
            if current_margin_usage > 0.9:
                self._emergency_position_reduction(account_name, client)
    
    def _emergency_position_reduction(self, account_name: str, client: OandaClient):
        """Emergency position reduction for critical margin usage"""
        try:
            positions = client.get_positions()
            open_positions = {k: v for k, v in positions.items() 
                            if v.long_units != 0 or v.short_units != 0}
            
            if not open_positions:
                return
            
            # Close 50% of largest losing positions
            losing_positions = [(inst, pos) for inst, pos in open_positions.items() 
                              if pos.unrealized_pl < 0]
            losing_positions.sort(key=lambda x: x[1].unrealized_pl)
            
            positions_to_close = losing_positions[:len(losing_positions)//2]
            
            for instrument, position in positions_to_close:
                try:
                    if position.long_units > 0:
                        close_units = position.long_units // 2
                        client.place_market_order(instrument, -close_units)
                    elif position.short_units > 0:
                        close_units = abs(position.short_units) // 2
                        client.place_market_order(instrument, close_units)
                    
                    logger.info(f"🚨 Emergency position reduction: {instrument} for {account_name}")
                    
                except Exception as e:
                    logger.error(f"❌ Failed to close position {instrument}: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Emergency position reduction failed for {account_name}: {e}")
    
    def _send_adaptation_notification(self, account_name: str, condition: MarketCondition, 
                                    adapted_params: RiskParameters):
        """Send adaptation notification via Telegram"""
        message = f"🤖 ADAPTIVE SYSTEM ALERT\n\n"
        message += f"📊 Account: {account_name}\n"
        message += f"⚠️ Condition: {condition.value.replace('_', ' ').title()}\n"
        message += f"🎯 Adaptation Level: {adapted_params.adaptation_level.value}\n\n"
        
        if adapted_params.position_size_multiplier < 1.0:
            reduction = int((1 - adapted_params.position_size_multiplier) * 100)
            message += f"📉 Position sizes reduced by {reduction}%\n"
        
        if adapted_params.trade_frequency == "paused":
            message += f"⏸️ New trades paused\n"
        
        message += f"🔒 Max margin usage: {adapted_params.max_margin_usage:.1%}\n"
        message += f"📈 Max positions: {adapted_params.max_positions}\n\n"
        message += f"⏰ Time: {datetime.now().strftime('%H:%M:%S')}"
        
        self.telegram_notifier.send_message(message)
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status"""
        return {
            'is_running': self.is_running,
            'current_condition': self.market_detector.get_current_market_condition().value,
            'active_signals': len(self.market_detector.market_signals),
            'risk_parameters': {name: asdict(params) for name, params in self.risk_manager.current_risk_parameters.items()},
            'last_adaptation_times': self.last_adaptation_time,
            'monitored_instruments': self.monitored_instruments
        }
    
    def save_learning_data(self, filename: str = None):
        """Save learning data for future analysis"""
        if filename is None:
            filename = f"adaptive_learning_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        data = {
            'timestamp': datetime.now().isoformat(),
            'market_signals': [
                {
                    'timestamp': signal.timestamp.isoformat(),
                    'signal_type': signal.signal_type,
                    'instrument': signal.instrument,
                    'value': signal.value,
                    'threshold': signal.threshold,
                    'condition': signal.condition.value,
                    'confidence': signal.confidence
                }
                for signal in self.market_detector.market_signals[-100:]  # Last 100 signals
            ],
            'current_conditions': {k: v.value for k, v in self.market_detector.current_conditions.items()},
            'risk_parameters': {name: {
                'position_size_multiplier': params.position_size_multiplier,
                'stop_loss_adjustment': params.stop_loss_adjustment,
                'take_profit_adjustment': params.take_profit_adjustment,
                'max_positions': params.max_positions,
                'trade_frequency': params.trade_frequency,
                'max_margin_usage': params.max_margin_usage,
                'adaptation_level': params.adaptation_level.value
            } for name, params in self.risk_manager.current_risk_parameters.items()},
            'system_status': self.get_system_status()
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"💾 Learning data saved to {filename}")
        return filename
