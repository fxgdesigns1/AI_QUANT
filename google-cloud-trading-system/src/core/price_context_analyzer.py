#!/usr/bin/env python3
"""
Price Context Analyzer - Multi-timeframe Analysis and Pattern Detection
Detects key price levels, patterns, and market structures
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from dataclasses import dataclass
import talib

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PricePattern(Enum):
    """Price patterns for technical analysis"""
    DOUBLE_TOP = "Double Top"
    DOUBLE_BOTTOM = "Double Bottom"
    HEAD_AND_SHOULDERS = "Head and Shoulders"
    INV_HEAD_AND_SHOULDERS = "Inverse Head and Shoulders"
    ASCENDING_TRIANGLE = "Ascending Triangle"
    DESCENDING_TRIANGLE = "Descending Triangle"
    SYMMETRICAL_TRIANGLE = "Symmetrical Triangle"
    BULLISH_FLAG = "Bullish Flag"
    BEARISH_FLAG = "Bearish Flag"
    BULLISH_PENNANT = "Bullish Pennant"
    BEARISH_PENNANT = "Bearish Pennant"
    RECTANGLE = "Rectangle"
    CUP_AND_HANDLE = "Cup and Handle"
    WEDGE = "Wedge"
    NONE = "No Pattern"

class CandlePattern(Enum):
    """Japanese candlestick patterns"""
    DOJI = "Doji"
    HAMMER = "Hammer"
    SHOOTING_STAR = "Shooting Star"
    ENGULFING_BULLISH = "Bullish Engulfing"
    ENGULFING_BEARISH = "Bearish Engulfing"
    MORNING_STAR = "Morning Star"
    EVENING_STAR = "Evening Star"
    THREE_WHITE_SOLDIERS = "Three White Soldiers"
    THREE_BLACK_CROWS = "Three Black Crows"
    NONE = "No Pattern"

@dataclass
class PriceLevel:
    """Key price level structure"""
    price: float
    type: str  # "support", "resistance", "pivot", "psychological"
    strength: float  # 0.0 to 1.0
    touches: int
    timeframe: str  # "M5", "M15", "H1", "H4", "D1"
    last_test: Optional[str] = None  # datetime of last test
    description: str = ""

@dataclass
class DetectedPattern:
    """Detected price pattern"""
    pattern: PricePattern
    start_idx: int
    end_idx: int
    strength: float  # 0.0 to 1.0
    target: Optional[float] = None
    stop: Optional[float] = None
    risk_reward: Optional[float] = None
    description: str = ""

@dataclass
class TimeframeContext:
    """Price context for a specific timeframe"""
    timeframe: str
    trend: str  # "bullish", "bearish", "neutral"
    momentum: float  # -1.0 to 1.0
    volatility: float
    support_levels: List[PriceLevel]
    resistance_levels: List[PriceLevel]
    patterns: List[DetectedPattern]
    key_levels: List[PriceLevel]

class PriceContextAnalyzer:
    """
    Multi-timeframe price context analyzer
    Detects key levels, patterns, and market structures
    """
    
    def __init__(self):
        """Initialize price context analyzer"""
        self.name = "Price Context Analyzer"
        
        # Timeframes to analyze
        self.timeframes = ["M5", "M15", "H1", "H4", "D1"]
        
        # Pattern detection settings
        self.pattern_lookback = 100  # Bars to look back for pattern detection
        self.min_pattern_quality = 0.7  # Minimum pattern quality (0.0 to 1.0)
        
        # Level detection settings
        self.support_resistance_lookback = 200  # Bars for S/R detection
        self.min_level_touches = 2  # Minimum touches to confirm a level
        self.level_tolerance = 0.0010  # 0.1% tolerance for level clustering
        
        # Volatility settings
        self.volatility_period = 14  # Period for ATR calculation
        
        # Psychological levels
        self.psychological_levels = []
        self.generate_psychological_levels()
        
        logger.info(f"✅ {self.name} initialized")
    
    def generate_psychological_levels(self):
        """Generate psychological price levels for common instruments"""
        # Forex major round numbers
        for base in [1.0, 1.1, 1.2, 1.3, 1.4, 1.5]:
            for i in range(10):
                self.psychological_levels.append(base + i * 0.1)
        
        # Gold round numbers
        for base in [1000, 1500, 2000, 2500, 3000, 3500, 4000, 4500]:
            for i in range(10):
                self.psychological_levels.append(base + i * 10)
    
    def analyze_price_context(self, instrument: str, 
                             price_data: Dict[str, pd.DataFrame]) -> Dict[str, TimeframeContext]:
        """
        Analyze price context across multiple timeframes
        
        Args:
            instrument: Instrument to analyze
            price_data: Dict of price DataFrames by timeframe
            
        Returns:
            Dict of TimeframeContext objects by timeframe
        """
        context_by_timeframe = {}
        
        for timeframe in self.timeframes:
            if timeframe not in price_data:
                continue
            
            df = price_data[timeframe]
            if len(df) < 30:
                logger.warning(f"⚠️ Not enough data for {instrument} {timeframe}")
                continue
            
            # Analyze this timeframe
            try:
                # Detect trend
                trend = self._detect_trend(df)
                
                # Calculate momentum
                momentum = self._calculate_momentum(df)
                
                # Calculate volatility
                volatility = self._calculate_volatility(df)
                
                # Find support and resistance levels
                support_levels = self._find_support_levels(df, instrument, timeframe)
                resistance_levels = self._find_resistance_levels(df, instrument, timeframe)
                
                # Detect patterns
                patterns = self._detect_patterns(df)
                
                # Combine all key levels
                key_levels = support_levels + resistance_levels
                key_levels.sort(key=lambda x: x.price)
                
                # Create timeframe context
                context = TimeframeContext(
                    timeframe=timeframe,
                    trend=trend,
                    momentum=momentum,
                    volatility=volatility,
                    support_levels=support_levels,
                    resistance_levels=resistance_levels,
                    patterns=patterns,
                    key_levels=key_levels
                )
                
                context_by_timeframe[timeframe] = context
                
            except Exception as e:
                logger.error(f"❌ Error analyzing {instrument} {timeframe}: {e}")
                continue
        
        return context_by_timeframe
    
    def _detect_trend(self, df: pd.DataFrame) -> str:
        """
        Detect trend direction using multiple indicators
        
        Args:
            df: Price DataFrame with OHLC data
            
        Returns:
            Trend direction: "bullish", "bearish", or "neutral"
        """
        try:
            # Use EMA crossovers
            df["ema20"] = talib.EMA(df["close"].values, timeperiod=20)
            df["ema50"] = talib.EMA(df["close"].values, timeperiod=50)
            
            # Current EMAs
            current_ema20 = df["ema20"].iloc[-1]
            current_ema50 = df["ema50"].iloc[-1]
            
            # EMA slope (last 5 bars)
            ema20_slope = df["ema20"].iloc[-1] - df["ema20"].iloc[-6]
            ema50_slope = df["ema50"].iloc[-1] - df["ema50"].iloc[-6]
            
            # Determine trend
            if current_ema20 > current_ema50 and ema20_slope > 0:
                return "bullish"
            elif current_ema20 < current_ema50 and ema20_slope < 0:
                return "bearish"
            else:
                return "neutral"
                
        except Exception as e:
            logger.warning(f"⚠️ Error detecting trend: {e}")
            return "neutral"
    
    def _calculate_momentum(self, df: pd.DataFrame) -> float:
        """
        Calculate momentum score (-1.0 to 1.0)
        
        Args:
            df: Price DataFrame with OHLC data
            
        Returns:
            Momentum score (-1.0 = strong bearish, 1.0 = strong bullish)
        """
        try:
            # Use RSI for momentum
            rsi = talib.RSI(df["close"].values, timeperiod=14)
            current_rsi = rsi[-1]
            
            # Normalize RSI to -1.0 to 1.0
            momentum = (current_rsi - 50) / 50
            
            return momentum
            
        except Exception as e:
            logger.warning(f"⚠️ Error calculating momentum: {e}")
            return 0.0
    
    def _calculate_volatility(self, df: pd.DataFrame) -> float:
        """
        Calculate volatility using ATR
        
        Args:
            df: Price DataFrame with OHLC data
            
        Returns:
            Volatility as percentage of price
        """
        try:
            # Calculate ATR
            atr = talib.ATR(df["high"].values, df["low"].values, 
                           df["close"].values, timeperiod=self.volatility_period)
            
            # Normalize by current price
            current_price = df["close"].iloc[-1]
            volatility = atr[-1] / current_price
            
            return volatility
            
        except Exception as e:
            logger.warning(f"⚠️ Error calculating volatility: {e}")
            return 0.0
    
    def _find_support_levels(self, df: pd.DataFrame, instrument: str, 
                            timeframe: str) -> List[PriceLevel]:
        """
        Find support levels
        
        Args:
            df: Price DataFrame with OHLC data
            instrument: Instrument being analyzed
            timeframe: Timeframe being analyzed
            
        Returns:
            List of support PriceLevel objects
        """
        support_levels = []
        
        try:
            # Find local minima
            for i in range(5, len(df) - 5):
                if (df["low"].iloc[i] <= df["low"].iloc[i-1] and 
                    df["low"].iloc[i] <= df["low"].iloc[i-2] and
                    df["low"].iloc[i] <= df["low"].iloc[i+1] and
                    df["low"].iloc[i] <= df["low"].iloc[i+2]):
                    
                    # Potential support level
                    level_price = df["low"].iloc[i]
                    
                    # Check if near existing level
                    is_near_existing = False
                    for level in support_levels:
                        if abs(level_price - level.price) / level.price < self.level_tolerance:
                            # Update existing level
                            level.touches += 1
                            level.strength = min(1.0, level.strength + 0.1)
                            is_near_existing = True
                            break
                    
                    if not is_near_existing:
                        # Add new level
                        support_levels.append(PriceLevel(
                            price=level_price,
                            type="support",
                            strength=0.5,  # Initial strength
                            touches=1,
                            timeframe=timeframe,
                            description=f"{instrument} {timeframe} support"
                        ))
            
            # Add psychological levels
            current_price = df["close"].iloc[-1]
            for psych_level in self.psychological_levels:
                # Only add levels below current price
                if psych_level < current_price and psych_level > current_price * 0.9:
                    support_levels.append(PriceLevel(
                        price=psych_level,
                        type="psychological",
                        strength=0.4,  # Initial strength
                        touches=0,
                        timeframe=timeframe,
                        description=f"{instrument} psychological level"
                    ))
            
            # Filter by minimum touches
            support_levels = [level for level in support_levels 
                             if level.type == "psychological" or level.touches >= self.min_level_touches]
            
            # Sort by price
            support_levels.sort(key=lambda x: x.price, reverse=True)
            
            return support_levels
            
        except Exception as e:
            logger.warning(f"⚠️ Error finding support levels: {e}")
            return []
    
    def _find_resistance_levels(self, df: pd.DataFrame, instrument: str, 
                               timeframe: str) -> List[PriceLevel]:
        """
        Find resistance levels
        
        Args:
            df: Price DataFrame with OHLC data
            instrument: Instrument being analyzed
            timeframe: Timeframe being analyzed
            
        Returns:
            List of resistance PriceLevel objects
        """
        resistance_levels = []
        
        try:
            # Find local maxima
            for i in range(5, len(df) - 5):
                if (df["high"].iloc[i] >= df["high"].iloc[i-1] and 
                    df["high"].iloc[i] >= df["high"].iloc[i-2] and
                    df["high"].iloc[i] >= df["high"].iloc[i+1] and
                    df["high"].iloc[i] >= df["high"].iloc[i+2]):
                    
                    # Potential resistance level
                    level_price = df["high"].iloc[i]
                    
                    # Check if near existing level
                    is_near_existing = False
                    for level in resistance_levels:
                        if abs(level_price - level.price) / level.price < self.level_tolerance:
                            # Update existing level
                            level.touches += 1
                            level.strength = min(1.0, level.strength + 0.1)
                            is_near_existing = True
                            break
                    
                    if not is_near_existing:
                        # Add new level
                        resistance_levels.append(PriceLevel(
                            price=level_price,
                            type="resistance",
                            strength=0.5,  # Initial strength
                            touches=1,
                            timeframe=timeframe,
                            description=f"{instrument} {timeframe} resistance"
                        ))
            
            # Add psychological levels
            current_price = df["close"].iloc[-1]
            for psych_level in self.psychological_levels:
                # Only add levels above current price
                if psych_level > current_price and psych_level < current_price * 1.1:
                    resistance_levels.append(PriceLevel(
                        price=psych_level,
                        type="psychological",
                        strength=0.4,  # Initial strength
                        touches=0,
                        timeframe=timeframe,
                        description=f"{instrument} psychological level"
                    ))
            
            # Filter by minimum touches
            resistance_levels = [level for level in resistance_levels 
                                if level.type == "psychological" or level.touches >= self.min_level_touches]
            
            # Sort by price
            resistance_levels.sort(key=lambda x: x.price)
            
            return resistance_levels
            
        except Exception as e:
            logger.warning(f"⚠️ Error finding resistance levels: {e}")
            return []
    
    def _detect_patterns(self, df: pd.DataFrame) -> List[DetectedPattern]:
        """
        Detect chart patterns
        
        Args:
            df: Price DataFrame with OHLC data
            
        Returns:
            List of DetectedPattern objects
        """
        patterns = []
        
        try:
            # Use TALib pattern recognition
            # Double Top
            pattern_result = talib.CDLDOUBLEUP(df["open"].values, df["high"].values, 
                                              df["low"].values, df["close"].values)
            for i in range(len(pattern_result)):
                if pattern_result[i] > 0:
                    patterns.append(DetectedPattern(
                        pattern=PricePattern.DOUBLE_TOP,
                        start_idx=max(0, i-10),
                        end_idx=i,
                        strength=0.8,
                        description="Double Top pattern"
                    ))
            
            # Double Bottom
            pattern_result = talib.CDLDOUBLEDOWN(df["open"].values, df["high"].values, 
                                                df["low"].values, df["close"].values)
            for i in range(len(pattern_result)):
                if pattern_result[i] > 0:
                    patterns.append(DetectedPattern(
                        pattern=PricePattern.DOUBLE_BOTTOM,
                        start_idx=max(0, i-10),
                        end_idx=i,
                        strength=0.8,
                        description="Double Bottom pattern"
                    ))
            
            # Head and Shoulders (approximation)
            pattern_result = talib.CDLHIKKAKE(df["open"].values, df["high"].values, 
                                             df["low"].values, df["close"].values)
            for i in range(len(pattern_result)):
                if pattern_result[i] < 0:
                    patterns.append(DetectedPattern(
                        pattern=PricePattern.HEAD_AND_SHOULDERS,
                        start_idx=max(0, i-20),
                        end_idx=i,
                        strength=0.7,
                        description="Head and Shoulders pattern"
                    ))
            
            # Inverse Head and Shoulders (approximation)
            for i in range(len(pattern_result)):
                if pattern_result[i] > 0:
                    patterns.append(DetectedPattern(
                        pattern=PricePattern.INV_HEAD_AND_SHOULDERS,
                        start_idx=max(0, i-20),
                        end_idx=i,
                        strength=0.7,
                        description="Inverse Head and Shoulders pattern"
                    ))
            
            # Filter by minimum quality
            patterns = [p for p in patterns if p.strength >= self.min_pattern_quality]
            
            return patterns
            
        except Exception as e:
            logger.warning(f"⚠️ Error detecting patterns: {e}")
            return []
    
    def detect_candlestick_patterns(self, df: pd.DataFrame) -> List[Tuple[int, CandlePattern, float]]:
        """
        Detect Japanese candlestick patterns
        
        Args:
            df: Price DataFrame with OHLC data
            
        Returns:
            List of (index, pattern, strength) tuples
        """
        patterns = []
        
        try:
            # Doji
            doji = talib.CDLDOJI(df["open"].values, df["high"].values, 
                                df["low"].values, df["close"].values)
            for i in range(len(doji)):
                if doji[i] != 0:
                    patterns.append((i, CandlePattern.DOJI, 0.6))
            
            # Hammer
            hammer = talib.CDLHAMMER(df["open"].values, df["high"].values, 
                                    df["low"].values, df["close"].values)
            for i in range(len(hammer)):
                if hammer[i] != 0:
                    patterns.append((i, CandlePattern.HAMMER, 0.7))
            
            # Shooting Star
            shooting_star = talib.CDLSHOOTINGSTAR(df["open"].values, df["high"].values, 
                                                df["low"].values, df["close"].values)
            for i in range(len(shooting_star)):
                if shooting_star[i] != 0:
                    patterns.append((i, CandlePattern.SHOOTING_STAR, 0.7))
            
            # Engulfing
            engulfing = talib.CDLENGULFING(df["open"].values, df["high"].values, 
                                          df["low"].values, df["close"].values)
            for i in range(len(engulfing)):
                if engulfing[i] > 0:
                    patterns.append((i, CandlePattern.ENGULFING_BULLISH, 0.8))
                elif engulfing[i] < 0:
                    patterns.append((i, CandlePattern.ENGULFING_BEARISH, 0.8))
            
            # Morning Star
            morning_star = talib.CDLMORNINGSTAR(df["open"].values, df["high"].values, 
                                              df["low"].values, df["close"].values)
            for i in range(len(morning_star)):
                if morning_star[i] != 0:
                    patterns.append((i, CandlePattern.MORNING_STAR, 0.9))
            
            # Evening Star
            evening_star = talib.CDLEVENINGSTAR(df["open"].values, df["high"].values, 
                                              df["low"].values, df["close"].values)
            for i in range(len(evening_star)):
                if evening_star[i] != 0:
                    patterns.append((i, CandlePattern.EVENING_STAR, 0.9))
            
            return patterns
            
        except Exception as e:
            logger.warning(f"⚠️ Error detecting candlestick patterns: {e}")
            return []
    
    def is_near_key_level(self, price: float, key_levels: List[PriceLevel], 
                         tolerance: float = 0.0010) -> Tuple[bool, Optional[PriceLevel]]:
        """
        Check if price is near a key level
        
        Args:
            price: Current price
            key_levels: List of key levels
            tolerance: Percentage tolerance (default: 0.1%)
            
        Returns:
            Tuple of (is_near, level)
        """
        for level in key_levels:
            if abs(price - level.price) / price < tolerance:
                return True, level
        
        return False, None
    
    def get_multi_timeframe_trend(self, contexts: Dict[str, TimeframeContext]) -> str:
        """
        Get overall trend across multiple timeframes
        
        Args:
            contexts: Dict of TimeframeContext by timeframe
            
        Returns:
            Overall trend: "bullish", "bearish", or "neutral"
        """
        # Timeframe weights (higher weight for longer timeframes)
        weights = {
            "M5": 0.1,
            "M15": 0.15,
            "H1": 0.25,
            "H4": 0.25,
            "D1": 0.25
        }
        
        bullish_score = 0.0
        bearish_score = 0.0
        total_weight = 0.0
        
        for timeframe, context in contexts.items():
            weight = weights.get(timeframe, 0.1)
            total_weight += weight
            
            if context.trend == "bullish":
                bullish_score += weight
            elif context.trend == "bearish":
                bearish_score += weight
        
        if total_weight == 0:
            return "neutral"
        
        bullish_pct = bullish_score / total_weight
        bearish_pct = bearish_score / total_weight
        
        if bullish_pct > 0.6:
            return "bullish"
        elif bearish_pct > 0.6:
            return "bearish"
        else:
            return "neutral"
    
    def get_trade_context(self, instrument: str, price: float, 
                         contexts: Dict[str, TimeframeContext]) -> Dict[str, Any]:
        """
        Get comprehensive trade context for decision making
        
        Args:
            instrument: Instrument being analyzed
            price: Current price
            contexts: Dict of TimeframeContext by timeframe
            
        Returns:
            Dict with trade context information
        """
        # Get overall trend
        overall_trend = self.get_multi_timeframe_trend(contexts)
        
        # Find nearest support and resistance
        nearest_support = None
        nearest_resistance = None
        
        for timeframe in ["H1", "H4", "D1"]:
            if timeframe in contexts:
                # Find nearest support below price
                supports = [level for level in contexts[timeframe].support_levels if level.price < price]
                if supports:
                    nearest_s = max(supports, key=lambda x: x.price)
                    if nearest_support is None or nearest_s.price > nearest_support.price:
                        nearest_support = nearest_s
                
                # Find nearest resistance above price
                resistances = [level for level in contexts[timeframe].resistance_levels if level.price > price]
                if resistances:
                    nearest_r = min(resistances, key=lambda x: x.price)
                    if nearest_resistance is None or nearest_r.price < nearest_resistance.price:
                        nearest_resistance = nearest_r
        
        # Calculate risk-reward potential
        risk_reward = 0.0
        if nearest_support and nearest_resistance:
            distance_to_support = price - nearest_support.price
            distance_to_resistance = nearest_resistance.price - price
            
            if distance_to_support > 0:
                risk_reward = distance_to_resistance / distance_to_support
        
        # Check for patterns
        recent_patterns = []
        for timeframe, context in contexts.items():
            for pattern in context.patterns:
                recent_patterns.append({
                    "timeframe": timeframe,
                    "pattern": pattern.pattern.value,
                    "strength": pattern.strength,
                    "description": pattern.description
                })
        
        # Compile context
        trade_context = {
            "instrument": instrument,
            "current_price": price,
            "overall_trend": overall_trend,
            "nearest_support": nearest_support.price if nearest_support else None,
            "nearest_resistance": nearest_resistance.price if nearest_resistance else None,
            "risk_reward": risk_reward,
            "recent_patterns": recent_patterns,
            "timeframes": {}
        }
        
        # Add timeframe-specific data
        for timeframe, context in contexts.items():
            trade_context["timeframes"][timeframe] = {
                "trend": context.trend,
                "momentum": context.momentum,
                "volatility": context.volatility
            }
        
        return trade_context


# Global instance
_price_context_analyzer = None

def get_price_context_analyzer() -> PriceContextAnalyzer:
    """Get the global price context analyzer instance"""
    global _price_context_analyzer
    if _price_context_analyzer is None:
        _price_context_analyzer = PriceContextAnalyzer()
    return _price_context_analyzer


if __name__ == "__main__":
    # Test price context analyzer
    import yfinance as yf
    
    analyzer = get_price_context_analyzer()
    
    # Download some test data
    symbol = "EURUSD=X"
    data = yf.download(symbol, period="60d", interval="1h")
    
    # Convert to expected format
    df = pd.DataFrame({
        "open": data["Open"],
        "high": data["High"],
        "low": data["Low"],
        "close": data["Close"],
        "volume": data["Volume"]
    })
    
    # Create multi-timeframe data
    price_data = {
        "H1": df
    }
    
    # Analyze price context
    contexts = analyzer.analyze_price_context("EUR_USD", price_data)
    
    # Print results
    for timeframe, context in contexts.items():
        print(f"\nTimeframe: {timeframe}")
        print(f"Trend: {context.trend}")
        print(f"Momentum: {context.momentum:.2f}")
        print(f"Volatility: {context.volatility:.4f}")
        
        print("\nSupport Levels:")
        for level in context.support_levels[:3]:
            print(f"- {level.price:.5f} (Strength: {level.strength:.1f}, Touches: {level.touches})")
        
        print("\nResistance Levels:")
        for level in context.resistance_levels[:3]:
            print(f"- {level.price:.5f} (Strength: {level.strength:.1f}, Touches: {level.touches})")
        
        print("\nPatterns:")
        for pattern in context.patterns:
            print(f"- {pattern.pattern.value} (Strength: {pattern.strength:.1f})")
    
    # Get trade context
    current_price = df["close"].iloc[-1]
    trade_context = analyzer.get_trade_context("EUR_USD", current_price, contexts)
    
    print("\nTrade Context:")
    print(f"Overall Trend: {trade_context['overall_trend']}")
    if trade_context["nearest_support"]:
        print(f"Nearest Support: {trade_context['nearest_support']:.5f}")
    else:
        print("No support found")
    if trade_context["nearest_resistance"]:
        print(f"Nearest Resistance: {trade_context['nearest_resistance']:.5f}")
    else:
        print("No resistance found")
    print(f"Risk-Reward: {trade_context['risk_reward']:.2f}")
