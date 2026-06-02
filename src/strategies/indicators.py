#!/usr/bin/env python3
"""
Technical Indicator Calculations
RSI, MACD, Bollinger Bands, ATR, EMA calculations
"""

import pandas as pd
import numpy as np
from typing import List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


def calculate_rsi(closes: List[float], period: int = 14) -> Optional[float]:
    """Calculate Relative Strength Index (RSI)
    
    Args:
        closes: List of closing prices
        period: RSI period (default 14)
    
    Returns:
        RSI value (0-100) or None if insufficient data
    """
    if len(closes) < period + 1:
        return None
    
    df = pd.DataFrame({'close': closes})
    delta = df['close'].diff()
    
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=period).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    rsi_val = rsi.iloc[-1]
    return float(rsi_val) if not pd.isna(rsi_val) else None


def calculate_macd(closes: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Optional[Tuple[float, float, float]]:
    """Calculate MACD (Moving Average Convergence Divergence)
    
    Args:
        closes: List of closing prices
        fast: Fast EMA period (default 12)
        slow: Slow EMA period (default 26)
        signal: Signal line EMA period (default 9)
    
    Returns:
        Tuple of (MACD line, Signal line, Histogram) or None if insufficient data
    """
    if len(closes) < slow + signal:
        return None
    
    df = pd.DataFrame({'close': closes})
    
    # Calculate EMAs
    ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
    ema_slow = df['close'].ewm(span=slow, adjust=False).mean()
    
    # MACD line
    macd_line = ema_fast - ema_slow
    
    # Signal line (EMA of MACD)
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    
    # Histogram
    histogram = macd_line - signal_line
    
    macd_val = macd_line.iloc[-1]
    signal_val = signal_line.iloc[-1]
    hist_val = histogram.iloc[-1]
    
    if pd.isna(macd_val) or pd.isna(signal_val) or pd.isna(hist_val):
        return None
    
    return (float(macd_val), float(signal_val), float(hist_val))


def calculate_bollinger_bands(closes: List[float], period: int = 20, std_dev: float = 2.0) -> Optional[Tuple[float, float, float]]:
    """Calculate Bollinger Bands
    
    Args:
        closes: List of closing prices
        period: Moving average period (default 20)
        std_dev: Standard deviation multiplier (default 2.0)
    
    Returns:
        Tuple of (Upper Band, Middle Band (SMA), Lower Band) or None if insufficient data
    """
    if len(closes) < period:
        return None
    
    df = pd.DataFrame({'close': closes})
    
    # Middle band (SMA)
    sma = df['close'].rolling(window=period).mean()
    
    # Standard deviation
    std = df['close'].rolling(window=period).std()
    
    # Upper and lower bands
    upper_band = sma + (std * std_dev)
    lower_band = sma - (std * std_dev)
    
    upper_val = upper_band.iloc[-1]
    middle_val = sma.iloc[-1]
    lower_val = lower_band.iloc[-1]
    
    if pd.isna(upper_val) or pd.isna(middle_val) or pd.isna(lower_val):
        return None
    
    return (float(upper_val), float(middle_val), float(lower_val))


def calculate_atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> Optional[float]:
    """Calculate Average True Range (ATR)
    
    Args:
        highs: List of high prices
        lows: List of low prices
        closes: List of closing prices
        period: ATR period (default 14)
    
    Returns:
        ATR value or None if insufficient data
    """
    if len(highs) < period + 1 or len(lows) < period + 1 or len(closes) < period + 1:
        return None
    
    df = pd.DataFrame({
        'high': highs,
        'low': lows,
        'close': closes
    })
    
    # Calculate True Range
    high_low = df['high'] - df['low']
    high_close = (df['high'] - df['close'].shift()).abs()
    low_close = (df['low'] - df['close'].shift()).abs()
    
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    
    # ATR is moving average of True Range
    atr = true_range.rolling(window=period).mean()
    
    atr_val = atr.iloc[-1]
    return float(atr_val) if not pd.isna(atr_val) else None


def calculate_ema(closes: List[float], period: int) -> Optional[float]:
    """Calculate Exponential Moving Average (EMA)
    
    Args:
        closes: List of closing prices
        period: EMA period
    
    Returns:
        EMA value or None if insufficient data
    """
    if len(closes) < period:
        return None
    
    df = pd.DataFrame({'close': closes})
    ema = df['close'].ewm(span=period, adjust=False).mean()
    
    ema_val = ema.iloc[-1]
    return float(ema_val) if not pd.isna(ema_val) else None


def calculate_sma(closes: List[float], period: int) -> Optional[float]:
    """Calculate Simple Moving Average (SMA)
    
    Args:
        closes: List of closing prices
        period: SMA period
    
    Returns:
        SMA value or None if insufficient data
    """
    if len(closes) < period:
        return None
    
    df = pd.DataFrame({'close': closes})
    sma = df['close'].rolling(window=period).mean()
    
    sma_val = sma.iloc[-1]
    return float(sma_val) if not pd.isna(sma_val) else None
