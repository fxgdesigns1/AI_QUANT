#!/usr/bin/env python3
"""
Enhanced Adaptive Trading System with Full AI Integration
Includes: London Session Automation, News Filters, Mode Switching, Kill Switches
"""

import os
import sys
import json
import time
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

# Add project root to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, 'src'))

from src.core.oanda_client import OandaClient
from src.core.telegram_notifier import TelegramNotifier
from src.core.adaptive_system import (
    AdaptiveMarketDetector, AdaptiveRiskManager, 
    AdaptiveTradingSystem, MarketSignal
)

logger = logging.getLogger(__name__)

class TradingMode(Enum):
    AGGRESSIVE = "aggressive"
    BALANCED = "balanced"
    RELAXED = "relaxed"

class SessionType(Enum):
    LONDON = "london"
    NEW_YORK = "new_york"
    TOKYO = "tokyo"
    SYDNEY = "sydney"
    OVERLAP = "overlap"

@dataclass
class SessionConfig:
    """Trading session configuration"""
    name: str
    start_hour: int
    end_hour: int
    timezone: str
    volatility_multiplier: float
    max_positions: int
    risk_multiplier: float
    preferred_pairs: List[str]

@dataclass
class NewsEvent:
    """News event data"""
    title: str
    impact: str  # high, medium, low
    currency: str
    timestamp: datetime
    description: str

@dataclass
class TradingSignal:
    """Trading signal data"""
    timestamp: datetime
    instrument: str
    signal_type: str  # 'BUY', 'SELL'
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: float
    strategy: str
    reasoning: str

class TechnicalAnalyzer:
    """Technical analysis for opportunity detection"""
    
    def __init__(self):
        self.price_data = {}
        self.indicators = {}
        logger.info("📊 Technical Analyzer initialized")
    
    def add_price_data(self, instrument: str, prices: Dict[str, Any]):
        """Add price data for analysis"""
        if instrument not in self.price_data:
            self.price_data[instrument] = []
        
        self.price_data[instrument].append(prices)
        
        # Keep only last 100 data points
        if len(self.price_data[instrument]) > 100:
            self.price_data[instrument] = self.price_data[instrument][-100:]
    
    def calculate_ema(self, prices: List[float], period: int) -> float:
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return prices[-1] if prices else 0.0
        
        multiplier = 2 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    def calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calculate Relative Strength Index"""
        if len(prices) < period + 1:
            return 50.0
        
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        if len(gains) < period:
            return 50.0
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def scan_for_signals(self, instrument: str, confidence_threshold: float = 0.7) -> List[TradingSignal]:
        """Scan for trading signals"""
        signals = []
        
        if instrument not in self.price_data or len(self.price_data[instrument]) < 20:
            return signals
        
        prices = [float(p.get('close', 0)) for p in self.price_data[instrument]]
        current_price = prices[-1]
        
        # EMA Crossover Signal
        ema_3 = self.calculate_ema(prices, 3)
        ema_8 = self.calculate_ema(prices, 8)
        ema_21 = self.calculate_ema(prices, 21)
        
        if ema_3 > ema_8 > ema_21 and prices[-2] <= ema_8 and current_price > ema_8:
            # Bullish EMA crossover
            confidence = min(0.9, 0.6 + (ema_3 - ema_8) / current_price * 100)
            if confidence >= confidence_threshold:
                signals.append(TradingSignal(
                    timestamp=datetime.now(),
                    instrument=instrument,
                    signal_type='BUY',
                    entry_price=current_price,
                    stop_loss=current_price * 0.998,  # 0.2% stop loss
                    take_profit=current_price * 1.003,  # 0.3% take profit
                    confidence=confidence,
                    strategy='EMA_Crossover',
                    reasoning=f'EMA 3 ({ema_3:.5f}) crossed above EMA 8 ({ema_8:.5f})'
                ))
        
        elif ema_3 < ema_8 < ema_21 and prices[-2] >= ema_8 and current_price < ema_8:
            # Bearish EMA crossover
            confidence = min(0.9, 0.6 + (ema_8 - ema_3) / current_price * 100)
            if confidence >= confidence_threshold:
                signals.append(TradingSignal(
                    timestamp=datetime.now(),
                    instrument=instrument,
                    signal_type='SELL',
                    entry_price=current_price,
                    stop_loss=current_price * 1.002,  # 0.2% stop loss
                    take_profit=current_price * 0.997,  # 0.3% take profit
                    confidence=confidence,
                    strategy='EMA_Crossover',
                    reasoning=f'EMA 3 ({ema_3:.5f}) crossed below EMA 8 ({ema_8:.5f})'
                ))
        
        # RSI Signals
        rsi = self.calculate_rsi(prices)
        
        if rsi < 30:  # Oversold
            confidence = min(0.9, 0.7 + (30 - rsi) / 30 * 0.2)
            if confidence >= confidence_threshold:
                signals.append(TradingSignal(
                    timestamp=datetime.now(),
                    instrument=instrument,
                    signal_type='BUY',
                    entry_price=current_price,
                    stop_loss=current_price * 0.995,  # 0.5% stop loss
                    take_profit=current_price * 1.005,  # 0.5% take profit
                    confidence=confidence,
                    strategy='RSI_Oversold',
                    reasoning=f'RSI oversold at {rsi:.1f}'
                ))
        
        elif rsi > 70:  # Overbought
            confidence = min(0.9, 0.7 + (rsi - 70) / 30 * 0.2)
            if confidence >= confidence_threshold:
                signals.append(TradingSignal(
                    timestamp=datetime.now(),
                    instrument=instrument,
                    signal_type='SELL',
                    entry_price=current_price,
                    stop_loss=current_price * 1.005,  # 0.5% stop loss
                    take_profit=current_price * 0.995,  # 0.5% take profit
                    confidence=confidence,
                    strategy='RSI_Overbought',
                    reasoning=f'RSI overbought at {rsi:.1f}'
                ))
        
        return signals

class EnhancedAdaptiveSystem(AdaptiveTradingSystem):
    """Enhanced adaptive system with full AI integration and session automation"""
    
    def __init__(self, oanda_clients: Dict[str, OandaClient], telegram_notifier: TelegramNotifier = None):
        super().__init__(oanda_clients, telegram_notifier)
        
        # Enhanced configuration
        self.trading_mode = TradingMode.BALANCED
        self.kill_switches = {
            'emergency_stop': False,
            'pause_trading': False,
            'disable_news': False,
            'london_session_only': False
        }
        
        # Session configurations
        self.session_configs = {
            SessionType.LONDON: SessionConfig(
                name="London",
                start_hour=8,  # 8 AM GMT
                end_hour=17,   # 5 PM GMT
                timezone="GMT",
                volatility_multiplier=1.5,
                max_positions=8,
                risk_multiplier=1.2,
                preferred_pairs=['EUR_USD', 'GBP_USD', 'USD_JPY', 'XAU_USD']
            ),
            SessionType.NEW_YORK: SessionConfig(
                name="New York",
                start_hour=13,  # 1 PM GMT
                end_hour=22,    # 10 PM GMT
                timezone="GMT",
                volatility_multiplier=1.3,
                max_positions=6,
                risk_multiplier=1.1,
                preferred_pairs=['EUR_USD', 'GBP_USD', 'USD_CAD', 'XAU_USD']
            ),
            SessionType.TOKYO: SessionConfig(
                name="Tokyo",
                start_hour=0,   # 12 AM GMT
                end_hour=9,     # 9 AM GMT
                timezone="GMT",
                volatility_multiplier=0.8,
                max_positions=4,
                risk_multiplier=0.9,
                preferred_pairs=['USD_JPY', 'AUD_JPY', 'NZD_JPY']
            ),
            SessionType.OVERLAP: SessionConfig(
                name="London-NY Overlap",
                start_hour=13,  # 1 PM GMT
                end_hour=17,    # 5 PM GMT
                timezone="GMT",
                volatility_multiplier=2.0,
                max_positions=10,
                risk_multiplier=1.5,
                preferred_pairs=['EUR_USD', 'GBP_USD', 'USD_JPY', 'XAU_USD', 'USD_CAD']
            )
        }
        
        # News filters
        self.news_filters = {
            'high_impact_only': True,
            'currency_pairs': ['EUR_USD', 'GBP_USD', 'USD_JPY', 'XAU_USD'],
            'exclude_keywords': ['war', 'terrorism', 'pandemic', 'crisis'],
            'include_keywords': ['rate', 'inflation', 'gdp', 'employment', 'fed', 'ecb', 'boe']
        }
        
        # Strategy configurations per mode
        self.mode_configs = {
            TradingMode.AGGRESSIVE: {
                'max_daily_trades': 50,
                'position_size_multiplier': 1.5,
                'risk_per_trade': 0.5,  # 0.5%
                'take_profit_multiplier': 1.2,
                'stop_loss_multiplier': 0.8,
                'signal_cooldown': 180,  # 3 minutes
                'min_confidence': 0.6
            },
            TradingMode.BALANCED: {
                'max_daily_trades': 30,
                'position_size_multiplier': 1.0,
                'risk_per_trade': 0.3,  # 0.3%
                'take_profit_multiplier': 1.0,
                'stop_loss_multiplier': 1.0,
                'signal_cooldown': 300,  # 5 minutes
                'min_confidence': 0.7
            },
            TradingMode.RELAXED: {
                'max_daily_trades': 15,
                'position_size_multiplier': 0.7,
                'risk_per_trade': 0.2,  # 0.2%
                'take_profit_multiplier': 0.8,
                'stop_loss_multiplier': 1.2,
                'signal_cooldown': 600,  # 10 minutes
                'min_confidence': 0.8
            }
        }
        
        # Current session tracking
        self.current_session = None
        self.session_start_time = None
        self.trades_this_session = 0
        
        # News events cache
        self.news_events: List[NewsEvent] = []
        self.last_news_update = None
        
        logger.info("🚀 Enhanced Adaptive Trading System initialized")
        logger.info(f"📊 Trading Mode: {self.trading_mode.value}")
        logger.info(f"🛑 Kill Switches: {self.kill_switches}")
        logger.info(f"📰 News Filters: {self.news_filters}")
    
    def set_trading_mode(self, mode: str):
        """Set trading mode"""
        try:
            self.trading_mode = TradingMode(mode.lower())
            logger.info(f"📊 Trading mode changed to: {self.trading_mode.value}")
            
            # Update risk parameters
            self._update_mode_parameters()
            
            # Notify via Telegram
            if self.telegram_notifier:
                self.telegram_notifier.send_system_status(
                    'mode_change', 
                    f"Trading mode changed to {self.trading_mode.value.upper()}"
                )
            
            return True
        except ValueError:
            logger.error(f"❌ Invalid trading mode: {mode}")
            return False
    
    def _update_mode_parameters(self):
        """Update system parameters based on current mode"""
        config = self.mode_configs[self.trading_mode]
        
        # Update risk manager parameters
        if hasattr(self, 'risk_manager'):
            self.risk_manager.base_risk_per_trade = config['risk_per_trade']
            self.risk_manager.max_daily_trades = config['max_daily_trades']
        
        # Update signal cooldown
        self.signal_cooldown = config['signal_cooldown']
        
        logger.info(f"📊 Updated parameters for {self.trading_mode.value} mode")
    
    def toggle_strategy(self, strategy: str, enabled: bool):
        """Toggle strategy on/off"""
        if strategy in self.strategy_mapping:
            # Update strategy mapping
            if enabled:
                logger.info(f"✅ Strategy {strategy} enabled")
            else:
                logger.info(f"❌ Strategy {strategy} disabled")
            
            # Notify via Telegram
            if self.telegram_notifier:
                self.telegram_notifier.send_system_status(
                    'strategy_toggle',
                    f"Strategy {strategy} {'enabled' if enabled else 'disabled'}"
                )
            
            return True
        else:
            logger.error(f"❌ Invalid strategy: {strategy}")
            return False
    
    def emergency_stop(self):
        """Emergency stop all trading"""
        self.kill_switches['emergency_stop'] = True
        self.auto_trading_enabled = False
        
        # Close all positions if needed
        for account_name, client in self.oanda_clients.items():
            try:
                positions = client.get_positions()
                if positions:
                    logger.warning(f"🚨 Emergency stop: {len(positions)} positions open in {account_name}")
            except Exception as e:
                logger.error(f"❌ Error checking positions during emergency stop: {e}")
        
        logger.critical("🚨 EMERGENCY STOP ACTIVATED - All trading halted")
        
        # Notify via Telegram
        if self.telegram_notifier:
            self.telegram_notifier.send_system_status(
                'emergency_stop',
                "🚨 EMERGENCY STOP ACTIVATED - All trading activities halted"
            )
    
    def pause_trading(self):
        """Pause trading"""
        self.kill_switches['pause_trading'] = True
        logger.info("⏸️ Trading paused")
        
        if self.telegram_notifier:
            self.telegram_notifier.send_system_status('pause', "⏸️ Trading paused")
    
    def resume_trading(self):
        """Resume trading"""
        self.kill_switches['pause_trading'] = False
        logger.info("▶️ Trading resumed")
        
        if self.telegram_notifier:
            self.telegram_notifier.send_system_status('resume', "▶️ Trading resumed")
    
    def toggle_auto_trading(self, enabled: bool):
        """Toggle auto trading"""
        self.auto_trading_enabled = enabled
        logger.info(f"🤖 Auto trading {'enabled' if enabled else 'disabled'}")
        
        if self.telegram_notifier:
            self.telegram_notifier.send_system_status(
                'auto_trading',
                f"🤖 Auto trading {'enabled' if enabled else 'disabled'}"
            )
    
    def _get_current_session(self) -> Optional[SessionType]:
        """Determine current trading session"""
        now = datetime.utcnow()
        current_hour = now.hour
        
        # Check for session overlaps first
        if 13 <= current_hour < 17:  # London-NY Overlap
            return SessionType.OVERLAP
        elif 8 <= current_hour < 17:  # London Session
            return SessionType.LONDON
        elif 13 <= current_hour < 22:  # New York Session
            return SessionType.NEW_YORK
        elif 0 <= current_hour < 9:  # Tokyo Session
            return SessionType.TOKYO
        else:
            return None
    
    def _is_london_session_active(self) -> bool:
        """Check if London session is currently active"""
        current_session = self._get_current_session()
        return current_session in [SessionType.LONDON, SessionType.OVERLAP]
    
    def _get_session_config(self, session: SessionType) -> SessionConfig:
        """Get configuration for trading session"""
        return self.session_configs.get(session, self.session_configs[SessionType.LONDON])
    
    def _check_market_conditions(self):
        """Enhanced market condition checking with session awareness"""
        super()._check_market_conditions()
        
        # Check current session
        current_session = self._get_current_session()
        if current_session != self.current_session:
            self.current_session = current_session
            self.session_start_time = datetime.utcnow()
            self.trades_this_session = 0
            
            if current_session:
                session_config = self._get_session_config(current_session)
                logger.info(f"📊 {session_config.name} session started")
                
                # Notify session start
                if self.telegram_notifier:
                    self.telegram_notifier.send_system_status(
                        'session_start',
                        f"📊 {session_config.name} session started - Enhanced trading active"
                    )
        
        # Check for London session automation
        if self._is_london_session_active() and not self.kill_switches['london_session_only']:
            self._enhanced_london_session_trading()
        
        # Update news events
        self._update_news_events()
    
    def _enhanced_london_session_trading(self):
        """Enhanced trading during London session"""
        if self.kill_switches['emergency_stop'] or self.kill_switches['pause_trading']:
            return
        
        session_config = self._get_session_config(SessionType.LONDON)
        
        # Check if we should trade based on session rules
        if self.trades_this_session >= session_config.max_positions:
            return
        
        # Enhanced signal generation for London session
        self._generate_london_session_signals(session_config)
    
    def _generate_london_session_signals(self, session_config: SessionConfig):
        """Generate enhanced signals for London session"""
        try:
            # Get current prices for preferred pairs
            for instrument in session_config.preferred_pairs:
                if self._should_skip_instrument(instrument):
                    continue
                
                # Get prices
                prices = self._get_instrument_prices(instrument)
                if not prices:
                    continue
                
                # Add to technical analyzer
                self.technical_analyzer.add_price_data(instrument, prices)
                
                # Generate signals with enhanced parameters
                signals = self.technical_analyzer.scan_for_signals(
                    instrument, 
                    confidence_threshold=self.mode_configs[self.trading_mode]['min_confidence']
                )
                
                # Process signals with session-specific parameters
                for signal in signals:
                    if self._is_valid_signal(signal):
                        # Enhance signal for London session
                        enhanced_signal = self._enhance_signal_for_session(signal, session_config)
                        self._process_trading_signal(enhanced_signal)
                        
        except Exception as e:
            logger.error(f"❌ Error generating London session signals: {e}")
    
    def _enhance_signal_for_session(self, signal: TradingSignal, session_config: SessionConfig) -> TradingSignal:
        """Enhance signal parameters for current session"""
        # Apply session volatility multiplier
        volatility_mult = session_config.volatility_multiplier
        
        # Adjust TP/SL based on session
        tp_adjustment = volatility_mult * self.mode_configs[self.trading_mode]['take_profit_multiplier']
        sl_adjustment = volatility_mult * self.mode_configs[self.trading_mode]['stop_loss_multiplier']
        
        # Calculate enhanced TP/SL
        if signal.signal_type == 'BUY':
            enhanced_tp = signal.entry_price + (signal.take_profit - signal.entry_price) * tp_adjustment
            enhanced_sl = signal.entry_price - (signal.entry_price - signal.stop_loss) * sl_adjustment
        else:  # SELL
            enhanced_tp = signal.entry_price - (signal.entry_price - signal.take_profit) * tp_adjustment
            enhanced_sl = signal.entry_price + (signal.stop_loss - signal.entry_price) * sl_adjustment
        
        # Create enhanced signal
        enhanced_signal = TradingSignal(
            timestamp=signal.timestamp,
            instrument=signal.instrument,
            signal_type=signal.signal_type,
            entry_price=signal.entry_price,
            stop_loss=enhanced_sl,
            take_profit=enhanced_tp,
            confidence=signal.confidence * volatility_mult,
            strategy=f"{signal.strategy}_LONDON",
            reasoning=f"{signal.reasoning} (Enhanced for {session_config.name} session)"
        )
        
        return enhanced_signal
    
    def _should_skip_instrument(self, instrument: str) -> bool:
        """Check if instrument should be skipped based on news filters"""
        if self.kill_switches['disable_news']:
            return False
        
        # Check for high-impact news events
        for news in self.news_events:
            if news.impact == 'high' and news.currency in instrument:
                logger.info(f"📰 Skipping {instrument} due to high-impact news: {news.title}")
                return True
        
        return False
    
    def _update_news_events(self):
        """Update news events cache"""
        try:
            # Check if we need to update news (every 5 minutes)
            if (self.last_news_update and 
                datetime.utcnow() - self.last_news_update < timedelta(minutes=5)):
                return
            
            # Mock news events - replace with real news API
            current_news = [
                NewsEvent(
                    title="Fed Signals Potential Rate Cut",
                    impact="high",
                    currency="USD",
                    timestamp=datetime.utcnow(),
                    description="USD weakness expected, Gold bullish"
                ),
                NewsEvent(
                    title="ECB Maintains Current Policy",
                    impact="medium",
                    currency="EUR",
                    timestamp=datetime.utcnow(),
                    description="EUR stability, range-bound trading"
                )
            ]
            
            # Apply filters
            filtered_news = []
            for news in current_news:
                if self.news_filters['high_impact_only'] and news.impact != 'high':
                    continue
                
                # Check exclude keywords
                if any(keyword in news.title.lower() for keyword in self.news_filters['exclude_keywords']):
                    continue
                
                # Check include keywords
                if any(keyword in news.title.lower() for keyword in self.news_filters['include_keywords']):
                    filtered_news.append(news)
            
            self.news_events = filtered_news
            self.last_news_update = datetime.utcnow()
            
            if filtered_news:
                logger.info(f"📰 Updated news events: {len(filtered_news)} events")
            
        except Exception as e:
            logger.error(f"❌ Error updating news events: {e}")
    
    def _execute_trade(self, signal: TradingSignal, account: str, position_size: int):
        """Enhanced trade execution with session awareness"""
        if self.kill_switches['emergency_stop'] or self.kill_switches['pause_trading']:
            logger.warning(f"🚫 Trade execution blocked by kill switch")
            return
        
        # Check session limits
        if self.trades_this_session >= self._get_session_config(self.current_session).max_positions:
            logger.warning(f"🚫 Trade execution blocked: Session limit reached")
            return
        
        # Execute trade with enhanced parameters
        try:
            client = self.oanda_clients.get(account)
            if not client:
                logger.error(f"❌ No client found for account: {account}")
                return
            
            # Use limit orders with enhanced TP/SL
            order = client.place_limit_order(
                instrument=signal.instrument,
                units=position_size,
                price=signal.entry_price,
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit
            )
            
            if order:
                self.trades_this_session += 1
                logger.info(f"✅ Enhanced trade executed: {signal.instrument} {signal.signal_type} {position_size} units")
                
                # Send enhanced notification
                if self.telegram_notifier:
                    self.telegram_notifier.send_trade_notification(
                        account=account,
                        instrument=signal.instrument,
                        side=signal.signal_type,
                        units=position_size,
                        entry_price=signal.entry_price,
                        stop_loss=signal.stop_loss,
                        take_profit=signal.take_profit,
                        strategy=signal.strategy,
                        session=self.current_session.name if self.current_session else "Unknown"
                    )
            else:
                logger.error(f"❌ Failed to execute enhanced trade")
                
        except Exception as e:
            logger.error(f"❌ Error executing enhanced trade: {e}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        base_status = super().get_system_status()
        
        enhanced_status = {
            **base_status,
            'trading_mode': self.trading_mode.value,
            'current_session': self.current_session.name if self.current_session else None,
            'session_trades': self.trades_this_session,
            'kill_switches': self.kill_switches,
            'news_events_count': len(self.news_events),
            'london_session_active': self._is_london_session_active(),
            'next_session': self._get_next_session_info()
        }
        
        return enhanced_status
    
    def _get_next_session_info(self) -> Dict[str, Any]:
        """Get information about next trading session"""
        now = datetime.utcnow()
        current_hour = now.hour
        
        if current_hour < 8:  # Before London
            next_session = SessionType.LONDON
            hours_until = 8 - current_hour
        elif current_hour < 13:  # Before NY
            next_session = SessionType.NEW_YORK
            hours_until = 13 - current_hour
        elif current_hour < 22:  # Before Tokyo
            next_session = SessionType.TOKYO
            hours_until = 24 - current_hour + 0
        else:  # After Tokyo
            next_session = SessionType.LONDON
            hours_until = 24 - current_hour + 8
        
        return {
            'session': next_session.name,
            'hours_until': hours_until,
            'start_time': f"{next_session.value}_start"
        }
    
    def start_adaptive_monitoring(self):
        """Start the adaptive monitoring system"""
        if hasattr(super(), 'start_adaptive_monitoring'):
            super().start_adaptive_monitoring()
        else:
            # Start monitoring thread
            self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.monitoring_thread.start()
            logger.info("🔄 Enhanced adaptive monitoring started")
    
    def stop_adaptive_monitoring(self):
        """Stop the adaptive monitoring system"""
        if hasattr(super(), 'stop_adaptive_monitoring'):
            super().stop_adaptive_monitoring()
        else:
            self.running = False
            logger.info("🛑 Enhanced adaptive monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        self.running = True
        logger.info("🔄 Enhanced monitoring loop started")
        
        while self.running:
            try:
                # Check market conditions
                self._check_market_conditions()
                
                # Sleep for 30 seconds
                time.sleep(30)
                
            except Exception as e:
                logger.error(f"❌ Error in monitoring loop: {e}")
                time.sleep(60)  # Wait longer on error
    
    def save_learning_data(self) -> Optional[str]:
        """Save learning data"""
        try:
            if hasattr(super(), 'save_learning_data'):
                return super().save_learning_data()
            else:
                # Basic save implementation
                filename = f"enhanced_learning_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                data = {
                    'timestamp': datetime.now().isoformat(),
                    'trading_mode': self.trading_mode.value,
                    'session_trades': self.trades_this_session,
                    'kill_switches': self.kill_switches,
                    'news_events_count': len(self.news_events)
                }
                
                with open(filename, 'w') as f:
                    json.dump(data, f, indent=2)
                
                logger.info(f"💾 Enhanced learning data saved: {filename}")
                return filename
        except Exception as e:
            logger.error(f"❌ Failed to save learning data: {e}")
            return None
