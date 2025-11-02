#!/usr/bin/env python3
"""
SIMPLE TIMER SCANNER - NO WEBSOCKET, NO EVENTS, JUST WORKS
Scans every 5 minutes, generates signals, NO EXCUSES
"""

import logging
import threading
import time
from datetime import datetime
from typing import Dict, List

from .oanda_client import get_oanda_client
from .telegram_notifier import get_telegram_notifier
from .optimization_loader import load_optimization_results, apply_per_pair_to_ultra_strict, apply_per_pair_to_momentum, apply_per_pair_to_gold
from .yaml_manager import get_yaml_manager
from .economic_calendar import get_economic_calendar
from .trump_dna_framework import get_trump_dna_planner
from .adaptive_scanner_integration import AdaptiveScannerMixin
from src.strategies.ultra_strict_forex_optimized import get_ultra_strict_forex_strategy
from src.strategies.momentum_trading import get_momentum_trading_strategy
from src.strategies.gold_scalping_optimized import get_gold_scalping_strategy
from src.strategies.gbp_usd_optimized import get_strategy_rank_1, get_strategy_rank_2, get_strategy_rank_3
from src.strategies.champion_75wr import get_champion_75wr_strategy
from src.strategies.ultra_strict_v2 import get_ultra_strict_v2_strategy
from src.strategies.momentum_v2 import get_momentum_v2_strategy
from src.strategies.all_weather_70wr import get_all_weather_70wr_strategy

logger = logging.getLogger(__name__)

class SimpleTimerScanner:
    """Simple scanner that just scans every 5 minutes"""
    
    def __init__(self):
        self.oanda = get_oanda_client()
        self.notifier = get_telegram_notifier()
        self.economic_calendar = get_economic_calendar()
        self.trump_planner = get_trump_dna_planner()
        self.is_running = False
        self.scan_count = 0
        
        # Adaptive system tracking (from AdaptiveScannerMixin)
        self.last_signal_time = datetime.now()
        self.last_adaptation_time = datetime.now()
        self.signals_since_adaptation = 0
        self.wins_since_adaptation = 0
        self.losses_since_adaptation = 0
        self.adaptation_interval_minutes = 30
        self.no_signal_threshold_minutes = 60
        self.loosen_amount = 0.10
        self.tighten_amount = 0.05
        self.small_loosen_step = 0.05  # 5% per no-signal scan
        
        # Load strategies DYNAMICALLY from accounts.yaml
        yaml_mgr = get_yaml_manager()
        yaml_accounts = yaml_mgr.get_all_accounts()
        yaml_strategies = yaml_mgr.get_all_strategies()
        
        # Strategy loader mapping
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
        
        self.strategies = {}
        self.accounts = {}
        
        # Load strategies from YAML
        for acc in yaml_accounts:
            if acc.get('active', False):
                strategy_name = acc.get('strategy')
                display_name = acc.get('display_name', acc.get('name'))
                
                if strategy_name in strategy_loaders:
                    self.strategies[display_name] = strategy_loaders[strategy_name]()
                    self.accounts[display_name] = acc['id']
                    logger.info(f"✅ Loaded: {display_name} ({strategy_name}) → {acc['id']}")
        
        logger.info(f"✅ SimpleTimerScanner initialized with {len(self.strategies)} strategies from accounts.yaml")
        
        # Backfill on initialization (APScheduler version)
        logger.info("📥 Backfilling historical data on init...")
        try:
            self._backfill_all_strategies()
            logger.info("✅ Backfill complete!")
        except Exception as e:
            logger.error(f"⚠️ Backfill failed (will retry): {e}")
        
        self.is_running = True
    
    def start(self):
        """Start scanning - DEPRECATED for APScheduler, kept for compatibility"""
        logger.warning("⚠️ start() called but scanner now uses APScheduler")
        logger.info("APScheduler will handle scheduling - scanner ready")
        self.is_running = True
    
    def _backfill_all_strategies(self):
        """Backfill historical data for all strategies"""
        logger.info("📥 Backfilling historical data for all strategies...")
        
        try:
            # Get all unique instruments
            all_instruments = set()
            for strategy in self.strategies.values():
                if hasattr(strategy, 'instruments'):
                    all_instruments.update(strategy.instruments)
            
            logger.info(f"📥 Fetching historical data for {len(all_instruments)} instruments...")
            
            # Get 60 candles for each instrument (enough for 50-period indicators)
            for instrument in all_instruments:
                try:
                    candles = self.oanda.get_candles(instrument, count=60, granularity='M5')
                    
                    if candles and 'candles' in candles:
                        candle_list = candles['candles']
                        logger.info(f"📥 Got {len(candle_list)} candles for {instrument}")
                        
                        # Add to each strategy that trades this instrument
                        for strategy in self.strategies.values():
                            if hasattr(strategy, 'instruments') and instrument in strategy.instruments:
                                if not hasattr(strategy, 'price_history'):
                                    strategy.price_history = {}
                                if instrument not in strategy.price_history:
                                    strategy.price_history[instrument] = []
                                
                                # Add candles to history
                                for candle in candle_list:
                                    mid_price = float(candle['mid']['c'])
                                    strategy.price_history[instrument].append(mid_price)
                    
                except Exception as e:
                    logger.error(f"❌ Backfill failed for {instrument}: {e}")
            
            logger.info("✅ Historical data backfill complete!")
            
            # Log data availability
            for strategy_name, strategy in self.strategies.items():
                if hasattr(strategy, 'price_history'):
                    max_hist = max([len(v) for v in strategy.price_history.values()]) if strategy.price_history else 0
                    logger.info(f"   {strategy_name}: {max_hist} data points")
            
        except Exception as e:
            logger.error(f"❌ Backfill error: {e}")
    
    def _scan_loop(self):
        """Main scan loop - DEPRECATED for APScheduler"""
        logger.warning("⚠️ _scan_loop called but APScheduler handles scheduling now")
        # Not used with APScheduler - APScheduler calls _run_scan() directly
    
    def _run_scan(self):
        """Run one complete scan - WITH TRUMP DNA + ADAPTIVE"""
        try:
            self.scan_count += 1
            logger.info(f"⏰ TRUMP DNA SCAN #{self.scan_count} at {datetime.now().strftime('%H:%M:%S')}")
            
            # ADAPTIVE SYSTEM: Check if we need to adjust thresholds
            self._check_and_adapt_thresholds()
            
            total_signals = 0
            aggregated_signals = []
            
            # Scan each strategy
            for strategy_name, account_id in self.accounts.items():
                try:
                    strategy = self.strategies[strategy_name]
                    
                    # Get instruments for this strategy
                    instruments = getattr(strategy, 'instruments', [])
                    if not instruments:
                        continue
                    
                    # ECONOMIC CALENDAR: Check if we should pause
                    should_pause = False
                    for inst in instruments:
                        try:
                            pause_needed, reason = self.economic_calendar.should_avoid_trading(inst)
                            if pause_needed:
                                logger.warning(f"⏸️  {strategy_name} ({inst}): Paused - {reason}")
                                should_pause = True
                                break
                        except AttributeError:
                            # Method doesn't exist, skip check
                            pass
                    
                    if should_pause:
                        continue
                    
                    # Get market data
                    market_data = {}
                    for inst in instruments:
                        try:
                            prices = self.oanda.get_current_prices([inst])
                            if inst in prices:
                                market_data[inst] = prices[inst]
                        except:
                            pass
                    
                    if not market_data:
                        continue
                    
                    # Update strategy price history if it has one
                    if hasattr(strategy, '_update_price_history'):
                        strategy._update_price_history(market_data)
                    
                    # Get price history length
                    hist_len = 0
                    if hasattr(strategy, 'price_history'):
                        for inst in instruments:
                            hist_len = max(hist_len, len(strategy.price_history.get(inst, [])))
                    
                    # Try to generate signals from strategy logic
                    signals = []
                    if hasattr(strategy, 'analyze_market'):
                        result = strategy.analyze_market(market_data)
                        if result:
                            if isinstance(result, list):
                                signals = result
                            else:
                                signals = [result]
                    
                    # TRUMP DNA: Also check sniper zones (simpler, more likely to trigger)
                    if not signals:
                        for inst in instruments:
                            if inst in market_data:
                                current_price = market_data[inst].ask
                                sniper_signal = self.trump_planner.get_entry_signal(inst, current_price, strategy_name)
                                
                                if sniper_signal:
                                    # Convert to strategy signal format
                                    signals.append({
                                        'instrument': inst,
                                        'direction': sniper_signal['action'],
                                        'confidence': 0.75,  # Sniper zones are high confidence
                                        'entry_price': current_price,
                                        'stop_loss': sniper_signal['stop_loss'],
                                        'take_profit': sniper_signal['take_profit'],
                                        'reason': f"Trump DNA sniper zone: {sniper_signal['reason']}",
                                        'source': 'trump_dna'
                                    })
                                    logger.info(f"🎯 {strategy_name}: Trump DNA sniper signal at {sniper_signal['zone_type']}")
                    
                    if signals:
                        total_signals += len(signals)
                        self.last_signal_time = datetime.now()
                        logger.info(f"🎯 {strategy_name}: {len(signals)} signals (history: {hist_len})")
                        # Collect for assessment and classification
                        for s in signals:
                            aggregated_signals.append((strategy_name, s))
                        
                        # EXECUTE TRADES for signals
                        for signal in signals:
                            try:
                                # Access TradeSignal as dataclass, not dictionary
                                instrument = signal.instrument if hasattr(signal, 'instrument') else signal.get('instrument') if isinstance(signal, dict) else None
                                direction = signal.side.name if hasattr(signal, 'side') else signal.get('direction') if isinstance(signal, dict) else None
                                confidence = signal.confidence if hasattr(signal, 'confidence') else signal.get('confidence', 0) if isinstance(signal, dict) else 0
                                
                                if not instrument or not direction:
                                    continue
                                
                                # Check economic calendar before entering
                                try:
                                    should_avoid, reason = self.economic_calendar.should_avoid_trading(instrument)
                                    if should_avoid:
                                        logger.warning(f"   ⏭️  Skipping {instrument} - {reason}")
                                        continue
                                except AttributeError:
                                    # Method doesn't exist, skip check
                                    pass
                                
                                # Check if already have position on this instrument
                                existing = self.oanda.get_open_trades()
                                # Handle both dict and object formats
                                existing_instruments = {
                                    t.get('instrument') if isinstance(t, dict) else getattr(t, 'instrument', None)
                                    for t in existing
                                }
                                if instrument in existing_instruments:
                                    logger.info(f"   ⏭️  Skipping {instrument} - already have position")
                                    continue
                                
                                # Place order
                                units = 500000 if direction == 'BUY' else -500000
                                if 'JPY' in instrument:
                                    tp_distance = 0.20 if direction == 'BUY' else -0.20
                                    sl_distance = -0.10 if direction == 'BUY' else 0.10
                                elif instrument == 'XAU_USD':
                                    units = 300 if direction == 'BUY' else -300
                                    tp_distance = 15.0 if direction == 'BUY' else -15.0
                                    sl_distance = -7.0 if direction == 'BUY' else 7.0
                                else:
                                    tp_distance = 0.0020 if direction == 'BUY' else -0.0020
                                    sl_distance = -0.0010 if direction == 'BUY' else 0.0010
                                
                                logger.info(f"   🔄 Placing order: {instrument} {direction} ({units} units)")
                                
                                # Get current price for entry
                                current_prices = self.oanda.get_current_prices([instrument], force_refresh=True)
                                current_price = current_prices[instrument]
                                entry_price = current_price.ask if direction == 'BUY' else current_price.bid
                                
                                # Calculate SL/TP as prices not distances
                                if direction == 'BUY':
                                    tp_price = entry_price + tp_distance
                                    sl_price = entry_price - sl_distance
                                else:
                                    tp_price = entry_price - tp_distance
                                    sl_price = entry_price + sl_distance
                                
                                result = self.oanda.place_market_order(
                                    instrument=instrument,
                                    units=units,
                                    take_profit=tp_price,
                                    stop_loss=sl_price
                                )
                                
                                if result:
                                    trade_id = result.trade_id if hasattr(result, 'trade_id') else 'N/A'
                                    logger.info(f"   ✅ ENTERED: {instrument} {direction} (ID: {trade_id})")
                                    # Send Telegram AFTER logging (don't let it block)
                                    try:
                                        self.notifier.send_message(
                                            f"✅ {strategy_name}\n{instrument} {direction}\nID: {trade_id}\nConfidence: {confidence:.0%}",
                                            'trade_entry'
                                        )
                                    except Exception as notif_error:
                                        logger.warning(f"   ⚠️ Telegram notification failed: {notif_error}")
                                else:
                                    error_msg = result.get('error', 'Unknown error') if result else 'No result returned'
                                    logger.warning(f"   ❌ Failed to enter {instrument} {direction}: {error_msg}")
                                    
                            except Exception as e:
                                logger.error(f"   ❌ Trade execution error: {e}")
                    else:
                        logger.info(f"   {strategy_name}: 0 signals (history: {hist_len})")
                        
                except Exception as e:
                    logger.error(f"❌ {strategy_name} error: {e}")
            
            if total_signals > 0:
                logger.info(f"📊 SCAN #{self.scan_count}: {total_signals} TOTAL SIGNALS")
                self.notifier.send_message(
                    f"🎯 SCAN COMPLETE\n{total_signals} signals generated!",
                    'trade_signal'
                )
                # Assess, validate, classify, and report
                try:
                    self._assess_validate_classify_and_report(aggregated_signals)
                except Exception as e:
                    logger.warning(f"⚠️ Classification/reporting failed: {e}")
            else:
                logger.info(f"📊 SCAN #{self.scan_count}: No signals (all strategies waiting for better conditions)")
                # Incrementally loosen criteria until signals start coming through (bounded)
                try:
                    self._incremental_loosen_small()
                    self.notifier.send_message(
                        "🔧 No signals. Incrementally loosening criteria slightly and re-scanning on schedule.",
                        'system_status'
                    )
                except Exception as e:
                    logger.warning(f"⚠️ Incremental loosen failed: {e}")
                
        except Exception as e:
            logger.error(f"❌ Scan failed: {e}")
            import traceback
            traceback.print_exc()
    
    def _check_and_adapt_thresholds(self):
        """ADAPTIVE SYSTEM: Auto-adjust thresholds based on market conditions"""
        now = datetime.now()
        
        # Session-aware gentle relaxation during London/NY overlap to increase opportunities
        # London prime time (user preference): 13:00-17:00 London time
        # We approximate via UTC hour checks used elsewhere in the codebase
        if 13 <= now.hour <= 17:
            try:
                # Apply a light session-based loosening without permanently drifting params
                for name, strategy in self.strategies.items():
                    # Loosen momentum and signal strength gates modestly
                    if hasattr(strategy, 'min_momentum'):
                        base_val = getattr(strategy, '_session_base_min_momentum', strategy.min_momentum)
                        setattr(strategy, '_session_base_min_momentum', base_val)
                        strategy.min_momentum = max(0.0003, base_val * 0.80)  # -20%
                    if hasattr(strategy, 'min_signal_strength'):
                        base_val = getattr(strategy, '_session_base_min_signal_strength', strategy.min_signal_strength)
                        setattr(strategy, '_session_base_min_signal_strength', base_val)
                        strategy.min_signal_strength = max(0.10, base_val * 0.90)  # -10%
                    if hasattr(strategy, 'min_adx'):
                        base_val = getattr(strategy, '_session_base_min_adx', strategy.min_adx)
                        setattr(strategy, '_session_base_min_adx', base_val)
                        strategy.min_adx = max(8.0, base_val * 0.90)  # -10%
            except Exception:
                # Non-fatal; continue with standard adaptation below
                pass
        else:
            # Outside overlap window: restore any session-adjusted parameters to their baselines
            for name, strategy in self.strategies.items():
                if hasattr(strategy, '_session_base_min_momentum'):
                    strategy.min_momentum = getattr(strategy, '_session_base_min_momentum')
                if hasattr(strategy, '_session_base_min_signal_strength'):
                    strategy.min_signal_strength = getattr(strategy, '_session_base_min_signal_strength')
                if hasattr(strategy, '_session_base_min_adx'):
                    strategy.min_adx = getattr(strategy, '_session_base_min_adx')

        # Only adapt every 30 minutes
        minutes_since_adaptation = (now - self.last_adaptation_time).total_seconds() / 60
        if minutes_since_adaptation < self.adaptation_interval_minutes:
            return
        
        # Check for no signals situation
        minutes_since_signal = (now - self.last_signal_time).total_seconds() / 60
        
        if minutes_since_signal > self.no_signal_threshold_minutes:
            self._loosen_all_thresholds()
            self.last_adaptation_time = now
            logger.warning(f"🔧 ADAPTIVE: No signals for {minutes_since_signal:.0f} min - loosening thresholds 10%")
        
        # Check win rate if we have enough data
        if self.signals_since_adaptation >= 10:
            win_rate = self.wins_since_adaptation / self.signals_since_adaptation
            
            if win_rate < 0.60:
                self._tighten_all_thresholds()
                self.last_adaptation_time = now
                logger.warning(f"🔧 ADAPTIVE: Win rate {win_rate:.1%} too low - tightening 5%")
            elif win_rate > 0.80:
                self._loosen_all_thresholds()
                self.last_adaptation_time = now
                logger.info(f"🔧 ADAPTIVE: Win rate {win_rate:.1%} excellent - loosening for more opportunities")
    
    def _loosen_all_thresholds(self):
        """Loosen all strategy thresholds by 10%"""
        for name, strategy in self.strategies.items():
            if hasattr(strategy, 'min_signal_strength'):
                old_val = strategy.min_signal_strength
                new_val = max(0.10, old_val * (1 - self.loosen_amount))
                strategy.min_signal_strength = new_val
                logger.info(f"📉 {name}: {old_val:.2f} → {new_val:.2f}")
            
            if hasattr(strategy, 'min_momentum'):
                old_val = strategy.min_momentum
                new_val = max(0.0003, old_val * (1 - self.loosen_amount))
                strategy.min_momentum = new_val
                logger.info(f"📉 {name}: momentum {old_val:.4f} → {new_val:.4f}")
        
        # Reset counters
        self.signals_since_adaptation = 0
        self.wins_since_adaptation = 0
        self.losses_since_adaptation = 0
    
    def _tighten_all_thresholds(self):
        """Tighten all strategy thresholds by 5%"""
        for name, strategy in self.strategies.items():
            if hasattr(strategy, 'min_signal_strength'):
                old_val = strategy.min_signal_strength
                new_val = min(0.50, old_val * (1 + self.tighten_amount))
                strategy.min_signal_strength = new_val
                logger.info(f"📈 {name}: {old_val:.2f} → {new_val:.2f}")
            
            if hasattr(strategy, 'min_momentum'):
                old_val = strategy.min_momentum
                new_val = min(0.005, old_val * (1 + self.tighten_amount))
                strategy.min_momentum = new_val
                logger.info(f"📈 {name}: momentum {old_val:.4f} → {new_val:.4f}")
        
        # Reset counters
        self.signals_since_adaptation = 0
        self.wins_since_adaptation = 0
        self.losses_since_adaptation = 0

    def _incremental_loosen_small(self):
        """Loosen thresholds a small step, bounded by safe floors."""
        for name, strategy in self.strategies.items():
            try:
                if hasattr(strategy, 'min_signal_strength'):
                    base = strategy.min_signal_strength
                    strategy.min_signal_strength = max(0.08, base * (1 - self.small_loosen_step))
                    logger.info(f"📉 {name}: min_signal_strength {base:.3f} → {strategy.min_signal_strength:.3f}")
                if hasattr(strategy, 'min_momentum'):
                    base = strategy.min_momentum
                    strategy.min_momentum = max(0.0003, base * (1 - self.small_loosen_step))
                    logger.info(f"📉 {name}: min_momentum {base:.5f} → {strategy.min_momentum:.5f}")
                if hasattr(strategy, 'min_adx'):
                    base = strategy.min_adx
                    strategy.min_adx = max(8.0, base * (1 - self.small_loosen_step))
                    logger.info(f"📉 {name}: min_adx {base:.2f} → {strategy.min_adx:.2f}")
            except Exception as e:
                logger.debug(f"Incremental loosen skip for {name}: {e}")

    def _assess_validate_classify_and_report(self, aggregated_signals):
        """Assess, validate, classify signals and send a concise Telegram summary."""
        if not aggregated_signals:
            return
        classes = { 'Elite': [], 'Good': [], 'Moderate': [], 'Reject': [] }
        total = 0
        for strat_name, sig in aggregated_signals:
            try:
                # Basic validation
                entry = getattr(sig, 'entry_price', None)
                sl = getattr(sig, 'stop_loss', None)
                tp = getattr(sig, 'take_profit', None)
                conf = float(getattr(sig, 'confidence', 0) or 0)
                side = getattr(sig, 'side', None)
                instrument = getattr(sig, 'instrument', 'UNKNOWN')
                if entry is None or sl is None or tp is None:
                    classes['Reject'].append((instrument, strat_name, 'invalid_prices'))
                    continue
                # RR calc
                risk = abs(entry - sl)
                reward = abs(tp - entry)
                rr = (reward / risk) if risk > 0 else 0
                # Classification
                if rr >= 2.0 and conf >= 0.6:
                    classes['Elite'].append((instrument, strat_name, rr, conf))
                elif rr >= 1.8 and conf >= 0.4:
                    classes['Good'].append((instrument, strat_name, rr, conf))
                elif rr >= 1.5 and conf >= 0.2:
                    classes['Moderate'].append((instrument, strat_name, rr, conf))
                else:
                    classes['Reject'].append((instrument, strat_name, f"rr={rr:.2f}", f"conf={conf:.2f}"))
                total += 1
            except Exception:
                classes['Reject'].append((getattr(sig, 'instrument', 'UNKNOWN'), strat_name, 'exception'))
        # Telegram summary
        summary = [
            "📊 Signal Assessment",
            f"Total reviewed: {total}",
            f"Elite: {len(classes['Elite'])}",
            f"Good: {len(classes['Good'])}",
            f"Moderate: {len(classes['Moderate'])}",
            f"Reject: {len(classes['Reject'])}",
        ]
        # Include short top-lines
        def fmt(items, n=3):
            return ", ".join([f"{i}/{s} rr={rr:.2f} conf={cf:.2f}" for (i,s,rr,cf) in items[:n]]) if items else "-"
        summary.append(f"Top Elite: {fmt(classes['Elite'])}")
        summary.append(f"Top Good: {fmt(classes['Good'])}")
        self.notifier.send_message("\n".join(summary), 'trade_signal')

# Global instance
_simple_scanner = None

def get_simple_scanner():
    """Get simple scanner instance"""
    global _simple_scanner
    if _simple_scanner is None:
        _simple_scanner = SimpleTimerScanner()
    return _simple_scanner

