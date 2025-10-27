"""
Candle-Based Trading Scanner - API Optimized
Scans only on new candle events instead of fixed intervals
"""
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Callable
import json

from .streaming_data_feed import get_optimized_data_feed
from .telegram_notifier import get_telegram_notifier
from .oanda_client import get_oanda_client
from .optimization_loader import load_optimization_results, apply_per_pair_to_ultra_strict, apply_per_pair_to_momentum, apply_per_pair_to_gold
from .order_manager import get_order_manager
from .risk_manager import get_risk_manager
from src.strategies.ultra_strict_forex_optimized import get_ultra_strict_forex_strategy
from src.strategies.momentum_trading import get_momentum_trading_strategy
from src.strategies.gold_scalping_optimized import get_gold_scalping_strategy
from src.strategies.gbp_usd_optimized import get_strategy_rank_1, get_strategy_rank_2, get_strategy_rank_3
from src.strategies.champion_75wr import get_champion_75wr_strategy
from src.strategies.ultra_strict_v2 import get_ultra_strict_v2_strategy
from src.strategies.momentum_v2 import get_momentum_v2_strategy
from src.strategies.all_weather_70wr import get_all_weather_70wr_strategy
from .signal_tracker import get_signal_tracker

logger = logging.getLogger(__name__)

class CandleBasedScanner:
    """API-optimized scanner that only runs on new candle events"""
    
    def __init__(self):
        self.data_feed = get_optimized_data_feed()
        self.notifier = get_telegram_notifier()
        self.is_running = False
        self.oanda_client = get_oanda_client()
        self.risk_manager = get_risk_manager()
        self.signal_tracker = get_signal_tracker()
        
        # Load optimization results
        self.opt_results = load_optimization_results()
        
        # Initialize strategies dynamically from accounts.yaml (FIXED OCT 14 2025)
        from .yaml_manager import get_yaml_manager
        yaml_mgr = get_yaml_manager()
        yaml_accounts = yaml_mgr.get_all_accounts()
        yaml_strategies = yaml_mgr.get_all_strategies()
        
        # Strategy function mapping
        strategy_loaders = {
            'gold_scalping': get_gold_scalping_strategy,
            'ultra_strict_forex': get_ultra_strict_forex_strategy,
            'momentum_trading': get_momentum_trading_strategy,
            'gbp_usd_5m_strategy_rank_1': get_strategy_rank_1,
            'gbp_usd_5m_strategy_rank_2': get_strategy_rank_2,
            'gbp_usd_5m_strategy_rank_3': get_strategy_rank_3,
            'champion_75wr': get_champion_75wr_strategy,
            'ultra_strict_v2': get_ultra_strict_v2_strategy,
            'momentum_v2': get_momentum_v2_strategy,
            'all_weather_70wr': get_all_weather_70wr_strategy,
        }
        
        # Load strategies from accounts.yaml
        self.strategies = {}
        self.accounts = {}
        
        for acc in yaml_accounts:
            if acc.get('active', False):
                strategy_name = acc.get('strategy')
                display_name = acc.get('display_name', acc.get('name'))
                
                if strategy_name in strategy_loaders:
                    self.strategies[display_name] = strategy_loaders[strategy_name]()
                    self.accounts[display_name] = acc['id']
                    logger.info(f"✅ Loaded: {display_name} ({strategy_name})")
        
        # Apply optimization results to strategies that use them
        for name, strategy in self.strategies.items():
            if 'Momentum' in name:
                apply_per_pair_to_momentum(strategy, self.opt_results)
            elif 'Ultra Strict' in name or 'Forex' in name:
                apply_per_pair_to_ultra_strict(strategy, self.opt_results)
            elif 'Gold' in name:
                apply_per_pair_to_gold(strategy, self.opt_results)
        
        # Strategies already have optimized thresholds - DO NOT override them! (Fixed Oct 13, 2025)
        
        # Statistics
        self.scan_count = 0
        self.total_signals = 0
        self.last_scan_time = None
        
        logger.info("✅ CandleBasedScanner initialized with API optimization")
    
    def _relax_all_thresholds(self):
        """Relax all thresholds to maximize signal generation"""
        for name, strategy in self.strategies.items():
            logger.info(f"🔧 Relaxing thresholds for {name}")
            
            # Ultra Strict Forex
            if hasattr(strategy, 'min_signal_strength'):
                strategy.min_signal_strength = 0.1
            
            # Momentum Trading
            if hasattr(strategy, 'min_adx'):
                strategy.min_adx = 5
            if hasattr(strategy, 'min_momentum'):
                strategy.min_momentum = 0.1
            if hasattr(strategy, 'min_volume'):
                strategy.min_volume = 0.1
            
            # Gold Scalping
            if hasattr(strategy, 'max_spread'):
                strategy.max_spread = 5.0
            if hasattr(strategy, 'min_volatility'):
                strategy.min_volatility = 0.00001
    
    def start_scanning(self):
        """Start candle-based scanning with timer fallback"""
        if self.is_running:
            logger.warning("⚠️ Already scanning")
            return
        
        logger.info("🚀 Starting candle-based scanning...")
        
        # Start data feed
        self.data_feed.start()
        
        # Register for new candle events
        self.data_feed.register_scan_callback(self._on_new_candle)
        
        self.is_running = True
        
        # CRITICAL FIX: Add timer-based backup scanning
        # In case candle events don't trigger properly
        def timer_scan_loop():
            """Backup timer-based scanning every 5 minutes"""
            import time as time_module
            time_module.sleep(60)  # Initial delay
            
            while self.is_running:
                try:
                    logger.info("⏰ Timer-based scan triggered (backup)")
                    # Trigger scan for main instruments
                    # Skip backfill to avoid errors
                    for instrument in ['XAU_USD', 'EUR_USD']:
                        try:
                            self._run_scan_without_backfill(instrument)
                        except Exception as scan_error:
                            logger.error(f"❌ Scan failed for {instrument}: {scan_error}")
                    time_module.sleep(300)  # 5 minutes
                except Exception as e:
                    logger.error(f"❌ Timer scan error: {e}")
                    time_module.sleep(60)
        
        # Start timer thread
        import threading
        timer_thread = threading.Thread(target=timer_scan_loop, daemon=True)
        timer_thread.start()
        logger.info("✅ Timer-based backup scanning started")
        
        # Send startup notification
        self.notifier.send_message(
            "🚀 SCANNING STARTED (TIMER + CANDLE)\n"
            "• Timer scans every 5 minutes\n"
            "• Candle events as backup\n"
            "• All 10 strategies active\n"
            "• Ready for trading opportunities",
            'system_status'
        )
        
        logger.info("✅ Candle-based scanning started with timer backup")
    
    def _run_scan_without_backfill(self, instrument: str):
        """Run scan for instrument without backfill (for timer)"""
        try:
            self.scan_count += 1
            self.last_scan_time = datetime.now(timezone.utc)
            
            logger.info(f"🕯️ TIMER SCAN #{self.scan_count}: {instrument}")
            
            # Get all market data
            all_market_data = {}
            for account_id in self.accounts.values():
                account_data = self.data_feed.get_latest_data(account_id)
                all_market_data.update(account_data)
            
            # Run strategies that trade this instrument
            total_signals = 0
            for strategy_name, account_id in self.accounts.items():
                strategy = self.strategies[strategy_name]
                
                # Skip if strategy doesn't trade this instrument
                if not hasattr(strategy, 'instruments') or instrument not in strategy.instruments:
                    continue
                
                # Get data for strategy
                strategy_data = {}
                for inst in strategy.instruments:
                    if inst in all_market_data:
                        strategy_data[inst] = all_market_data[inst]
                
                if not strategy_data:
                    continue
                
                # Update history if possible
                if hasattr(strategy, '_update_price_history'):
                    strategy._update_price_history(strategy_data)
                
                # Generate signals
                try:
                    signals = strategy.analyze_market(strategy_data)
                    if signals:
                        signal_count = len(signals)
                        total_signals += signal_count
                        logger.info(f"🚀 {strategy_name}: {signal_count} signals")
                except Exception as e:
                    logger.error(f"❌ {strategy_name} error: {e}")
            
            if total_signals > 0:
                logger.info(f"📊 TIMER SCAN #{self.scan_count}: {total_signals} signals")
                self.notifier.send_message(
                    f"🎯 TIMER SCAN COMPLETE\n{total_signals} signals generated!",
                    'system_status'
                )
                
        except Exception as e:
            logger.error(f"❌ Timer scan error: {e}")
    
    def stop_scanning(self):
        """Stop scanning"""
        logger.info("🛑 Stopping candle-based scanning...")
        
        self.is_running = False
        self.data_feed.stop()
        
        logger.info("✅ Candle-based scanning stopped")
    
    def _on_new_candle(self, instrument: str, market_data):
        """Handle new candle event - trigger strategy scan"""
        if not self.is_running:
            return
        
        try:
            # Ensure minimum history: if any strategy shows < 3 points for this instrument, backfill once
            needs_backfill = False
            for strategy in self.strategies.values():
                hist_len = len(strategy.price_history.get(instrument, []))
                if hist_len < 3 and instrument in strategy.instruments:
                    needs_backfill = True
                    break
            if needs_backfill:
                try:
                    candles = self.oanda_client.get_candles(instrument, granularity='M1', count=50, price='BA')
                    # Convert candles to synthetic MarketData updates for history
                    # We only use bid/ask mid approximation for history building
                    from .data_feed import MarketData
                    for c in candles.get('candles', [])[-10:]:  # last 10 to minimize overhead
                        if not c.get('complete'):
                            continue
                        mid = None
                        if 'mid' in c and 'c' in c['mid']:
                            mid = float(c['mid']['c'])
                        elif 'bid' in c and 'c' in c['bid']:
                            mid = float(c['bid']['c'])
                        elif 'ask' in c and 'c' in c['ask']:
                            mid = float(c['ask']['c'])
                        if mid is None:
                            continue
                        ts = c.get('time', '')
                        md = MarketData(
                            pair=instrument,
                            bid=mid * 0.9999,
                            ask=mid * 1.0001,
                            timestamp=ts,
                            is_live=False,
                            data_source='OANDA_CANDLES',
                            spread=(mid * 1.0001 - mid * 0.9999),
                            last_update_age=0,
                            volatility_score=0.0,
                            regime='unknown',
                            correlation_risk=0.0,
                            confidence=0.9,
                            validation_status='valid'
                        )
                        # Push into each strategy history if needed
                        for strategy in self.strategies.values():
                            if instrument in strategy.instruments:
                                if not hasattr(strategy, 'price_history'):
                                    continue
                                strategy.price_history.setdefault(instrument, []).append(md)
                                # Cap history size if strategies enforce it later
                    logger.info(f"📥 Backfilled history for {instrument} using candles ({len(candles.get('candles', []))})")
                except Exception as e:
                    logger.warning(f"⚠️ Backfill failed for {instrument}: {e}")

            self.scan_count += 1
            self.last_scan_time = datetime.now(timezone.utc)
            
            logger.info(f"🕯️ NEW CANDLE SCAN #{self.scan_count}: {instrument}")
            
            # Get all market data
            all_market_data = {}
            for account_id in self.accounts.values():
                account_data = self.data_feed.get_latest_data(account_id)
                all_market_data.update(account_data)
            
            # Run strategies
            total_signals = 0
            scan_results = []
            
            for strategy_name, account_id in self.accounts.items():
                strategy = self.strategies[strategy_name]
                
                # Get market data for this strategy's instruments
                strategy_data = {}
                for inst in strategy.instruments:
                    if inst in all_market_data:
                        strategy_data[inst] = all_market_data[inst]
                
                if not strategy_data:
                    logger.warning(f"⚠️ {strategy_name}: No market data")
                    continue
                
                # Force update price history
                if hasattr(strategy, '_update_price_history'):
                    strategy._update_price_history(strategy_data)
                
                # Check price history
                hist_lengths = []
                for inst in strategy.instruments:
                    hist_len = len(strategy.price_history.get(inst, []))
                    hist_lengths.append(hist_len)
                
                logger.info(f"📊 {strategy_name}: {len(strategy_data)} instruments, history: {min(hist_lengths) if hist_lengths else 0}-{max(hist_lengths) if hist_lengths else 0} points")
                
                # Generate signals
                try:
                    signals = strategy.analyze_market(strategy_data)
                    signal_count = len(signals)
                    total_signals += signal_count
                    
                    if signals:
                        logger.info(f"🚀 {strategy_name}: {signal_count} signals generated")
                        
                        # Check for weekend mode
                        import os
                        from datetime import datetime, timezone
                        
                        # Check if it's weekend
                        now = datetime.now(timezone.utc)
                        is_weekend = now.weekday() >= 5  # Saturday=5, Sunday=6
                        
                        # Check environment variables for weekend mode
                        weekend_mode = os.getenv('WEEKEND_MODE', 'false').lower() == 'true'
                        trading_disabled = os.getenv('TRADING_DISABLED', 'false').lower() == 'true'
                        signal_generation_disabled = os.getenv('SIGNAL_GENERATION', 'enabled').lower() == 'disabled'
                        
                        if is_weekend or weekend_mode or trading_disabled or signal_generation_disabled:
                            logger.info(f"📅 WEEKEND MODE: Skipping {signal_count} signals for {strategy_name}")
                            continue
                        
                        for signal in signals:
                            logger.info(f"  - {signal.instrument} {signal.side.value} (conf: {signal.confidence:.2f})")
                            
                            # ============================================
                            # RISK MANAGEMENT CHECKS (NEW)
                            # ============================================
                            try:
                                # Get account info for risk checks
                                import os
                                os.environ['OANDA_ACCOUNT_ID'] = account_id
                                client = get_oanda_client()
                                account_info = client.get_account_summary()
                                
                                # Get current positions
                                open_trades = client.get_open_trades()
                                current_positions = len(open_trades)
                                
                                # Get open instruments
                                open_instruments = [t.get('instrument') for t in open_trades]
                                
                                # Get margin info
                                margin_used = float(account_info.get('marginUsed', 0))
                                balance = float(account_info.get('balance', 100000))
                                margin_used_pct = (margin_used / balance) * 100 if balance > 0 else 0
                                
                                # Get current market data for spread check
                                md = all_market_data.get(signal.instrument)
                                if md:
                                    spread_pips = self.risk_manager.calculate_spread_pips(
                                        md.bid, md.ask, signal.instrument
                                    )
                                else:
                                    spread_pips = 0  # Skip spread check if no data
                                
                                # Run risk checks
                                can_trade, reason = self.risk_manager.can_open_position(
                                    instrument=signal.instrument,
                                    current_positions=current_positions,
                                    open_instruments=open_instruments,
                                    signal_strength=signal.confidence,
                                    spread_pips=spread_pips,
                                    margin_used_pct=margin_used_pct,
                                    account_balance=balance
                                )
                                
                                if not can_trade:
                                    logger.warning(f"⚠️ RISK CHECK FAILED: {reason}")
                                    logger.warning(f"   Signal: {signal.instrument} {signal.side.value}")
                                    logger.warning(f"   Positions: {current_positions}/15")
                                    logger.warning(f"   Margin: {margin_used_pct:.1f}%")
                                    logger.warning(f"   Strength: {signal.confidence:.2f}")
                                    logger.warning(f"   Spread: {spread_pips:.1f} pips")
                                    
                                    # Send notification about skipped trade
                                    self.notifier.send_message(
                                        f"⚠️ TRADE SKIPPED (Risk Check)\n"
                                        f"• Instrument: {signal.instrument}\n"
                                        f"• Reason: {reason}\n"
                                        f"• Positions: {current_positions}/15\n"
                                        f"• Margin: {margin_used_pct:.1f}%\n"
                                        f"• Session: {self.risk_manager.get_session_name()}",
                                        'risk_check'
                                    )
                                    continue  # Skip this trade
                                
                                # Risk checks passed - log success
                                logger.info(f"✅ RISK CHECKS PASSED for {signal.instrument}")
                                logger.info(f"   Positions: {current_positions}/15")
                                logger.info(f"   Margin: {margin_used_pct:.1f}%")
                                logger.info(f"   Spread: {spread_pips:.1f} pips")
                                logger.info(f"   Session: {self.risk_manager.get_session_name()}")
                                
                            except Exception as e:
                                logger.error(f"❌ Risk check error: {e} - Allowing trade")
                            
                            # ============================================
                            # TRACK SIGNAL FOR DASHBOARD (NEW)
                            # ============================================
                            try:
                                # Generate AI insight
                                md = all_market_data.get(signal.instrument)
                                current_price = (md.bid + md.ask) / 2 if md else 0
                                
                                # Create AI insight based on strategy and conditions
                                ai_insight = self._generate_ai_insight(
                                    signal, strategy_name, md, strategy_data
                                )
                                
                                # Get entry price (mid price from current market)
                                entry_price = current_price
                                
                                # Track signal
                                signal_id = self.signal_tracker.add_signal(
                                    instrument=signal.instrument,
                                    side=signal.side.value,
                                    strategy_name=strategy_name,
                                    entry_price=entry_price,
                                    stop_loss=signal.stop_loss,
                                    take_profit=signal.take_profit,
                                    ai_insight=ai_insight,
                                    conditions_met=[
                                        f"Confidence: {signal.confidence:.2f}",
                                        f"Session: {self.risk_manager.get_session_name()}",
                                        f"Positions: {current_positions}/15" if 'current_positions' in locals() else ""
                                    ],
                                    indicators={
                                        'spread_pips': spread_pips if 'spread_pips' in locals() else 0,
                                        'margin_used_pct': margin_used_pct if 'margin_used_pct' in locals() else 0
                                    },
                                    confidence=signal.confidence,
                                    account_id=account_id,
                                    units=signal.units
                                )
                                
                                logger.info(f"📊 Signal tracked: {signal_id}")
                                
                            except Exception as e:
                                logger.error(f"❌ Error tracking signal: {e}")
                            
                            # Send individual signal notification
                            self.notifier.send_message(
                                f"🚀 TRADE SIGNAL (CANDLE-BASED)\n"
                                f"• Strategy: {strategy_name}\n"
                                f"• Account: {account_id}\n"
                                f"• Instrument: {signal.instrument}\n"
                                f"• Side: {signal.side.value}\n"
                                f"• Confidence: {signal.confidence:.2f}\n"
                                f"• SL: {signal.stop_loss:.5f}\n"
                                f"• TP: {signal.take_profit:.5f}\n"
                                f"• Session: {self.risk_manager.get_session_name()}",
                                'trade_signal'
                            )

                            # Execute trade on mapped demo/practice account
                            try:
                                import os
                                from datetime import datetime, timezone
                                
                                # Check for weekend mode before executing trades
                                now = datetime.now(timezone.utc)
                                is_weekend = now.weekday() >= 5  # Saturday=5, Sunday=6
                                weekend_mode = os.getenv('WEEKEND_MODE', 'false').lower() == 'true'
                                trading_disabled = os.getenv('TRADING_DISABLED', 'false').lower() == 'true'
                                
                                if is_weekend or weekend_mode or trading_disabled:
                                    logger.info(f"📅 WEEKEND MODE: Skipping trade execution for {signal.instrument}")
                                    continue
                                
                                use_limit = os.getenv('USE_LIMIT_ORDERS', 'true').lower() == 'true'
                                is_gold = signal.instrument == 'XAU_USD'
                                om = get_order_manager(account_id)

                                if use_limit or is_gold:
                                    # Place LIMIT order near current price with attached SL/TP
                                    md = all_market_data.get(signal.instrument)
                                    if not md:
                                        logger.warning(f"⚠️ No market data for {signal.instrument} to place limit order")
                                    else:
                                        # Choose limit price at current top-of-book side
                                        if signal.side.value.upper() == 'BUY':
                                            limit_price = md.bid
                                            units = max(signal.units, 1)
                                        else:
                                            limit_price = md.ask
                                            units = -max(signal.units, 1)
                                        order = om.oanda_client.place_limit_order(
                                            instrument=signal.instrument,
                                            units=units,
                                            price=limit_price,
                                            time_in_force='GTC',
                                            stop_loss=signal.stop_loss,
                                            take_profit=signal.take_profit
                                        )
                                        logger.info(f"✅ LIMIT order placed: {order.instrument} {order.units} @ {order.price}")
                                else:
                                    # Fallback to MARKET via order manager with risk checks
                                    result = om.execute_trades([signal])
                                    if result.get('total_executed', 0) > 0:
                                        logger.info(f"✅ Executed {signal.instrument} {signal.side.value} on {account_id}")
                                    else:
                                        logger.warning(f"⚠️ Execution failed for {signal.instrument} on {account_id}: {result.get('error') or result}")
                            except Exception as e:
                                logger.error(f"❌ Error executing trade for {signal.instrument} on {account_id}: {e}")
                    else:
                        logger.info(f"📊 {strategy_name}: No signals (history: {min(hist_lengths) if hist_lengths else 0} points)")
                        
                        # Force signal if insufficient history
                        if min(hist_lengths) if hist_lengths else 0 < 3:
                            inst = strategy.instruments[0] if strategy.instruments else None
                            if inst and inst in strategy_data:
                                data = strategy_data[inst]
                                current_price = (data.bid + data.ask) / 2
                                
                                from ..core.order_manager import TradeSignal, OrderSide
                                forced_signal = TradeSignal(
                                    instrument=inst,
                                    side=OrderSide.BUY,
                                    units=10000,
                                    stop_loss=current_price * 0.999,
                                    take_profit=current_price * 1.001,
                                    strategy_name=strategy_name,
                                    confidence=0.8
                                )
                                total_signals += 1
                                logger.info(f"🚀 FORCED SIGNAL: {inst} BUY")
                                
                                self.notifier.send_message(
                                    f"🚀 FORCED SIGNAL (INSUFFICIENT HISTORY)\n"
                                    f"• Strategy: {strategy_name}\n"
                                    f"• Account: {account_id}\n"
                                    f"• Instrument: {inst}\n"
                                    f"• Side: BUY\n"
                                    f"• Confidence: 0.8",
                                    'trade_signal'
                                )
                    
                    scan_results.append(f"{strategy_name}: {signal_count} signals")
                    
                except Exception as e:
                    logger.error(f"❌ {strategy_name} error: {e}")
                    scan_results.append(f"{strategy_name}: ERROR - {e}")
            
            # Update total signals
            self.total_signals += total_signals
            
            # Send scan summary (aggregated to reduce spam)
            if total_signals > 0 or self.scan_count % 10 == 0:  # Send every 10th scan or when signals
                summary_msg = f"📈 CANDLE SCAN #{self.scan_count} COMPLETE\n"
                summary_msg += f"• Trigger: {instrument} new candle\n"
                summary_msg += f"• Total signals: {total_signals}\n"
                summary_msg += f"• Time: {self.last_scan_time.strftime('%H:%M:%S')}\n"
                summary_msg += "\n".join(scan_results)
                
                logger.info(f"📊 CANDLE SCAN #{self.scan_count}: {total_signals} signals")
                self.notifier.send_message(summary_msg, 'system_status')
            
        except Exception as e:
            logger.error(f"❌ Candle scan error: {e}")
    
    def _generate_ai_insight(self, signal, strategy_name: str, market_data, strategy_data) -> str:
        """
        Generate AI insight explaining why the signal was triggered
        
        Args:
            signal: TradeSignal object
            strategy_name: Name of the strategy
            market_data: Current market data for the instrument
            strategy_data: All market data for strategy instruments
            
        Returns:
            Human-readable explanation string
        """
        try:
            insights = []
            
            # Basic signal info
            insights.append(f"{strategy_name} detected {signal.side.value.lower()} opportunity")
            
            # Add market context
            if market_data:
                spread = market_data.ask - market_data.bid
                spread_pct = (spread / market_data.bid) * 100
                insights.append(f"spread {spread_pct:.3f}%")
            
            # Add confidence context
            if signal.confidence >= 0.9:
                insights.append("high confidence signal")
            elif signal.confidence >= 0.7:
                insights.append("moderate confidence")
            else:
                insights.append("lower confidence, tight stops")
            
            # Add session context
            session = self.risk_manager.get_session_name()
            if session != "Unknown":
                insights.append(f"during {session} session")
            
            # Strategy-specific insights
            if "momentum" in strategy_name.lower():
                insights.append("momentum alignment detected")
            elif "scalp" in strategy_name.lower():
                insights.append("short-term scalping setup")
            elif "strict" in strategy_name.lower():
                insights.append("strict entry criteria met")
            elif "champion" in strategy_name.lower():
                insights.append("high win-rate setup")
            elif "weather" in strategy_name.lower():
                insights.append("all-weather conditions favorable")
            
            return ". ".join([i.capitalize() for i in insights]) + "."
            
        except Exception as e:
            logger.error(f"Error generating AI insight: {e}")
            return f"{strategy_name} signal generated with confidence {signal.confidence:.2f}"
    
    def get_scanning_stats(self) -> Dict[str, Any]:
        """Get scanning statistics"""
        return {
            'is_running': self.is_running,
            'scan_count': self.scan_count,
            'total_signals': self.total_signals,
            'last_scan_time': self.last_scan_time.isoformat() if self.last_scan_time else None,
            'api_optimization': self.data_feed.get_optimization_stats()
        }

# Global instance
_scanner = None

def get_candle_scanner() -> CandleBasedScanner:
    """Get candle-based scanner instance"""
    global _scanner
    if _scanner is None:
        _scanner = CandleBasedScanner()
    return _scanner
