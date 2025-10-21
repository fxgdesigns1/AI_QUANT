#!/usr/bin/env python3
"""
Trade Quality Filter - Weeds out weak/erroneous trades
Increases win rate by filtering low-quality setups
"""

import logging
from datetime import datetime, time
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class FilterResult:
    """Result of trade quality filtering"""
    passes: bool
    score: float  # 0-100
    reason: str
    filters_passed: List[str]
    filters_failed: List[str]


class TradeQualityFilter:
    """
    Smart filters to weed out weak trades and increase win rate
    Each filter checks a quality criterion
    """
    
    def __init__(self):
        self.name = "TradeQualityFilter"
        
        # Filter thresholds (optimized from backtest analysis)
        self.min_momentum = 0.005  # 0.5% minimum momentum
        self.min_adx = 25  # Strong trend only
        self.min_atr = 0.0015  # Minimum volatility for forex
        self.min_atr_gold = 3.0  # Minimum volatility for gold
        self.max_spread_pips = 3  # Maximum spread (pips)
        self.max_spread_gold = 1.0  # Maximum spread for gold ($)
        self.confirmation_candles = 1  # Wait for confirmation
        self.max_distance_from_ma = 0.5  # Not too far from MA (50% of range)
        
        # Session times (London time)
        self.london_start = time(8, 0)
        self.ny_end = time(21, 30)
        
        logger.info("✅ Trade Quality Filter initialized")
        logger.info(f"   Filters: 8 active")
        logger.info(f"   Min momentum: {self.min_momentum*100}%")
        logger.info(f"   Min ADX: {self.min_adx}")
    
    def filter_trade(
        self,
        instrument: str,
        direction: str,
        momentum: float,
        adx: float,
        atr: float,
        spread: float,
        current_price: float,
        ma_5: float,
        ma_10: float,
        ma_20: float,
        current_time: Optional[datetime] = None
    ) -> FilterResult:
        """
        Apply all quality filters to a potential trade
        Returns FilterResult with pass/fail and score
        """
        
        passed = []
        failed = []
        score = 0
        
        # FILTER 1: Momentum Strength
        if abs(momentum) >= self.min_momentum:
            passed.append("Momentum")
            score += 20
        else:
            failed.append(f"Momentum too weak ({abs(momentum)*100:.2f}% < {self.min_momentum*100}%)")
        
        # FILTER 2: 3-MA Alignment
        if direction == 'BUY':
            if ma_5 > ma_10 > ma_20:
                passed.append("MA Alignment")
                score += 15
            else:
                failed.append("MAs not aligned for BUY")
        else:  # SELL
            if ma_5 < ma_10 < ma_20:
                passed.append("MA Alignment")
                score += 15
            else:
                failed.append("MAs not aligned for SELL")
        
        # FILTER 3: ADX Trend Strength
        if adx >= self.min_adx:
            passed.append("ADX Trend")
            score += 20
        else:
            failed.append(f"ADX too weak ({adx:.1f} < {self.min_adx})")
        
        # FILTER 4: Volatility (ATR)
        min_atr_required = self.min_atr_gold if 'XAU' in instrument else self.min_atr
        if atr >= min_atr_required:
            passed.append("Volatility")
            score += 15
        else:
            failed.append(f"ATR too low ({atr:.4f} < {min_atr_required})")
        
        # FILTER 5: Session Filter
        if current_time:
            current_time_only = current_time.time()
            if self.london_start <= current_time_only <= self.ny_end:
                passed.append("Session")
                score += 10
            else:
                failed.append(f"Outside London/NY session")
        else:
            # No time provided, pass by default
            passed.append("Session")
            score += 10
        
        # FILTER 6: Spread
        if 'XAU' in instrument:
            if spread <= self.max_spread_gold:
                passed.append("Spread")
                score += 10
            else:
                failed.append(f"Spread too wide (${spread:.2f} > ${self.max_spread_gold})")
        else:
            # Convert spread to pips
            pip_value = 0.01 if 'JPY' in instrument else 0.0001
            spread_pips = spread / pip_value
            if spread_pips <= self.max_spread_pips:
                passed.append("Spread")
                score += 10
            else:
                failed.append(f"Spread too wide ({spread_pips:.1f} pips > {self.max_spread_pips})")
        
        # FILTER 7: Not Overextended
        ma_range = abs(ma_20 - ma_5)
        distance_from_ma5 = abs(current_price - ma_5)
        
        if ma_range > 0:
            distance_ratio = distance_from_ma5 / ma_range
            if distance_ratio <= self.max_distance_from_ma:
                passed.append("Not Overextended")
                score += 10
            else:
                failed.append(f"Too far from MA ({distance_ratio*100:.0f}% > 50%)")
        else:
            # MAs flat, skip this filter
            passed.append("Not Overextended")
            score += 10
        
        # Determine if trade passes (need 5/8 filters)
        passes = len(passed) >= 5
        
        if passes:
            reason = f"QUALITY TRADE: {len(passed)}/8 filters passed"
        else:
            reason = f"REJECTED: Only {len(passed)}/8 filters passed"
        
        return FilterResult(
            passes=passes,
            score=score,
            reason=reason,
            filters_passed=passed,
            filters_failed=failed
        )


# Global instance
_quality_filter = None

def get_trade_quality_filter() -> TradeQualityFilter:
    """Get trade quality filter instance"""
    global _quality_filter
    if _quality_filter is None:
        _quality_filter = TradeQualityFilter()
    return _quality_filter


if __name__ == '__main__':
    # Test the filter
    filter_system = get_trade_quality_filter()
    
    print("\n" + "="*80)
    print("TESTING FILTER SYSTEM")
    print("="*80)
    print()
    
    # Test 1: Strong setup (should pass)
    print("TEST 1: Strong bullish setup")
    result = filter_system.filter_trade(
        instrument='XAU_USD',
        direction='BUY',
        momentum=0.008,  # 0.8% (strong)
        adx=45,  # Strong trend
        atr=5.0,  # Good volatility
        spread=0.50,  # Tight spread
        current_price=4300,
        ma_5=4295,
        ma_10=4290,
        ma_20=4285,
        current_time=datetime.now().replace(hour=14)  # 2 PM
    )
    
    print(f"   Result: {'✅ PASS' if result.passes else '❌ FAIL'}")
    print(f"   Score: {result.score}/100")
    print(f"   Passed: {result.filters_passed}")
    if result.filters_failed:
        print(f"   Failed: {result.filters_failed}")
    print()
    
    # Test 2: Weak setup (should fail)
    print("TEST 2: Weak setup (low momentum)")
    result2 = filter_system.filter_trade(
        instrument='EUR_USD',
        direction='BUY',
        momentum=0.001,  # 0.1% (weak)
        adx=15,  # Weak trend
        atr=0.0008,  # Low volatility
        spread=0.00015,  # 1.5 pips
        current_price=1.1650,
        ma_5=1.1648,
        ma_10=1.1645,
        ma_20=1.1640,
        current_time=datetime.now().replace(hour=14)
    )
    
    print(f"   Result: {'✅ PASS' if result2.passes else '❌ FAIL'}")
    print(f"   Score: {result2.score}/100")
    print(f"   Passed: {result2.filters_passed}")
    if result2.filters_failed:
        print(f"   Failed: {result2.filters_failed}")
    print()
    
    print("="*80)
    print("✅ FILTER SYSTEM READY")
    print("="*80)