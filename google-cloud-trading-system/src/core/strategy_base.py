#!/usr/bin/env python3
"""
Strategy Base Class - Common Functionality for ALL Strategies
Includes critical price history prefilling that ALL strategies need
"""

import logging
import os
import requests
from typing import Dict, List
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def prefill_price_history_for_strategy(strategy, instruments: List[str], 
                                       granularity: str = 'M15', count: int = 50):
    """
    UNIVERSAL FIX: Pre-fill price history for ANY strategy
    
    This is the critical fix that ALL strategies need!
    Without this, strategies start with empty history and can't generate signals.
    
    Args:
        strategy: Any strategy instance with .price_history attribute
        instruments: List of instruments to prefill
        granularity: Candle size ('M5', 'M15', 'H1')
        count: Number of candles to fetch (default 50)
    
    Returns:
        Total number of bars loaded
    """
    try:
        logger.info(f"📥 Pre-filling price history for {strategy.name if hasattr(strategy, 'name') else 'strategy'}...")
        
        # Get credentials from environment
        api_key = os.environ.get('OANDA_API_KEY', 'c01de9eb4d793c945ea0fcbb0620cc4e-d0c62eb93ed53e8db5a709089460794a')
        base_url = os.environ.get('OANDA_BASE_URL', 'https://api-fxpractice.oanda.com')
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        total_loaded = 0
        
        # Ensure price_history dict exists
        if not hasattr(strategy, 'price_history'):
            strategy.price_history = {}
        
        # Get historical candles for each instrument
        for instrument in instruments:
            try:
                url = f"{base_url}/v3/instruments/{instrument}/candles"
                params = {'count': count, 'granularity': granularity, 'price': 'M'}
                
                response = requests.get(url, headers=headers, params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    candles = data.get('candles', [])
                    
                    # Initialize list if needed
                    if instrument not in strategy.price_history:
                        strategy.price_history[instrument] = []
                    
                    # Add closes to history
                    for candle in candles:
                        mid = candle.get('mid', {})
                        close = float(mid.get('c', 0))
                        if close > 0:
                            strategy.price_history[instrument].append(close)
                    
                    bars_loaded = len(strategy.price_history[instrument])
                    total_loaded += bars_loaded
                    logger.info(f"  ✅ {instrument}: {bars_loaded} bars loaded")
                else:
                    logger.debug(f"  ⚠️ {instrument}: HTTP {response.status_code}")
                    
            except Exception as e:
                logger.debug(f"  ⚠️ {instrument}: {e}")
                continue
        
        if total_loaded > 0:
            logger.info(f"✅ Price history pre-filled: {total_loaded} total bars - READY TO TRADE!")
            return total_loaded
        else:
            logger.warning("⚠️ Price history prefill failed - will build from live feed")
            return 0
        
    except Exception as e:
        logger.warning(f"⚠️ Could not pre-fill price history: {e}")
        return 0


def apply_universal_fixes_to_strategy(strategy):
    """
    Apply all universal fixes to any strategy
    
    Call this in __init__ of every strategy:
    from src.core.strategy_base import apply_universal_fixes_to_strategy
    apply_universal_fixes_to_strategy(self)
    """
    # Fix 1: Prefill price history
    if hasattr(strategy, 'instruments') and hasattr(strategy, 'price_history'):
        prefill_price_history_for_strategy(strategy, strategy.instruments)
    
    # Fix 2: Ensure no forced minimum trades
    if hasattr(strategy, 'min_trades_today'):
        strategy.min_trades_today = 0
        logger.info("✅ Forced trades disabled (min_trades_today = 0)")
    
    # Fix 3: Set realistic quality thresholds
    if hasattr(strategy, 'min_quality_score'):
        if strategy.min_quality_score > 50:
            old_val = strategy.min_quality_score
            strategy.min_quality_score = 30  # Realistic
            logger.info(f"✅ Quality threshold lowered: {old_val} → 30 (realistic)")
    
    return strategy










