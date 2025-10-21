#!/usr/bin/env python3
"""
Pips Calculator Utility
Calculates pip values for different instrument types
"""
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

# Instruments that use 0.01 as a pip (JPY pairs)
JPY_PAIRS = ['USD_JPY', 'EUR_JPY', 'GBP_JPY', 'AUD_JPY', 'NZD_JPY', 'CAD_JPY', 'CHF_JPY']

# Gold and other metals use different pip values
METAL_INSTRUMENTS = {
    'XAU_USD': 0.01,  # Gold: $0.01 per troy ounce
    'XAG_USD': 0.001,  # Silver: $0.001 per troy ounce
}

def get_pip_value(instrument: str) -> float:
    """
    Get the pip value for an instrument
    
    Args:
        instrument: Trading instrument (e.g., 'EUR_USD', 'USD_JPY')
        
    Returns:
        Pip value as a float
    """
    # Check if it's a metal
    if instrument in METAL_INSTRUMENTS:
        return METAL_INSTRUMENTS[instrument]
    
    # Check if it's a JPY pair
    if instrument in JPY_PAIRS:
        return 0.01
    
    # Default for most forex pairs
    return 0.0001

def calculate_pips(instrument: str, price1: float, price2: float) -> float:
    """
    Calculate the pip difference between two prices
    
    Args:
        instrument: Trading instrument
        price1: First price (typically entry or current)
        price2: Second price (typically target or stop)
        
    Returns:
        Pip difference (positive if price2 > price1)
    """
    try:
        pip_value = get_pip_value(instrument)
        price_diff = price2 - price1
        pips = price_diff / pip_value
        return round(pips, 1)
    except Exception as e:
        logger.error(f"Error calculating pips for {instrument}: {e}")
        return 0.0

def calculate_pips_to_target(current: float, target: float, instrument: str) -> float:
    """
    Calculate pips from current price to target (SL or TP)
    
    Args:
        current: Current market price
        target: Target price (stop loss or take profit)
        instrument: Trading instrument
        
    Returns:
        Pips to target (positive value)
    """
    pips = calculate_pips(instrument, current, target)
    return abs(pips)

def format_pips(pips: float, show_sign: bool = True) -> str:
    """
    Format pips value as a string with sign
    
    Args:
        pips: Pip value
        show_sign: Whether to show + for positive values
        
    Returns:
        Formatted string (e.g., "+12.5", "-5.0")
    """
    if pips > 0 and show_sign:
        return f"+{pips:.1f}"
    return f"{pips:.1f}"

def get_pip_color(pips: float, is_approaching: bool = True) -> str:
    """
    Get color code for pip display
    
    Args:
        pips: Pip value
        is_approaching: True if approaching target is good (pending signals),
                       False if distance increasing is good (active trades)
        
    Returns:
        Color string: 'green', 'red', or 'neutral'
    """
    if is_approaching:
        # For pending signals: smaller pips = closer to entry = green
        if abs(pips) < 5:
            return 'green'
        elif abs(pips) < 15:
            return 'neutral'
        else:
            return 'red'
    else:
        # For active trades: positive pips = profit = green
        if pips > 0:
            return 'green'
        elif pips < 0:
            return 'red'
        else:
            return 'neutral'

def calculate_risk_reward_ratio(entry: float, stop_loss: float, take_profit: float, 
                                instrument: str) -> Tuple[float, float, float]:
    """
    Calculate risk/reward ratio for a trade
    
    Args:
        entry: Entry price
        stop_loss: Stop loss price
        take_profit: Take profit price
        instrument: Trading instrument
        
    Returns:
        Tuple of (risk_pips, reward_pips, risk_reward_ratio)
    """
    try:
        risk_pips = abs(calculate_pips(instrument, entry, stop_loss))
        reward_pips = abs(calculate_pips(instrument, entry, take_profit))
        
        if risk_pips > 0:
            rr_ratio = reward_pips / risk_pips
        else:
            rr_ratio = 0.0
            
        return (risk_pips, reward_pips, rr_ratio)
    except Exception as e:
        logger.error(f"Error calculating R/R ratio: {e}")
        return (0.0, 0.0, 0.0)

def format_instrument_display(instrument: str) -> str:
    """
    Format instrument name for display
    
    Args:
        instrument: Instrument code (e.g., 'EUR_USD')
        
    Returns:
        Formatted string (e.g., 'EUR/USD')
    """
    return instrument.replace('_', '/')



