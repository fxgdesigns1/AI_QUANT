#!/usr/bin/env python3
"""
Probe Step 2: Signal Generation Probe
Verify whether ANY strategy generated a signal for XAUUSD.
"""
import sys
import os
import logging
import json

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src.strategies.gold_scalping import GoldScalpingStrategy
from src.control_plane.market_data_provider import get_latest_price, get_candles

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("probe_signal_generation")

def probe_signal_generation():
    instrument = "XAU_USD"
    logger.info(f"Probing signal generation for {instrument}...")
    
    try:
        # Setup mock market data structure expected by strategy
        # GoldScalpingStrategy.analyze_market expects dict[instrument, Price]
        price = get_latest_price(instrument)
        market_data = {
            instrument: price
        }
        
        # Initialize strategy
        strategy = GoldScalpingStrategy()
        
        # Force evaluate
        signals = strategy.analyze_market(market_data)
        
        if signals:
            logger.info(f"SUCCESS: Generated {len(signals)} signals.")
            for s in signals:
                logger.info(f"Signal: {s.side} {s.instrument} @ {s.entry_price} (Conf: {s.metadata.get('confidence', 'N/A')})")
        else:
            logger.warning("NO SIGNALS generated.")
            # Dig deeper - why?
            # Check spread
            spread = price.ask - price.bid
            logger.info(f"Current Spread: {spread:.2f} (Max allowed: {strategy.max_spread_pips_xauusd})")
            
            # Check Confidence/Regime if possible
            if strategy.regime_detector:
                candles = get_candles(instrument, granularity="M5", count=60)
                regime_analysis = strategy.regime_detector.detect_regime(instrument, candles)
                logger.info(f"Detected Regime: {regime_analysis.regime}")
                logger.info(f"Volatility: {regime_analysis.volatility}")

    except Exception as e:
        logger.error(f"Probe failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    probe_signal_generation()
