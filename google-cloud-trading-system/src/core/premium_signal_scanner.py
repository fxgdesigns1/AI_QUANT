#!/usr/bin/env python3
"""
Premium Signal Scanner - Hybrid Lane
Finds 5-10 HIGH-QUALITY setups per day for manual approval
"""

import logging
from datetime import datetime, time
from typing import List, Dict, Optional
from dataclasses import dataclass
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)

@dataclass
class PremiumSignal:
    """Premium trade signal with quality score"""
    id: str
    timestamp: datetime
    instrument: str
    direction: str  # BUY or SELL
    entry_price: float
    tp_price: float
    sl_price: float
    score: int  # 0-100
    reasoning: str
    confidence: float
    r_r_ratio: float
    status: str = 'pending'  # pending, approved, rejected, executed
    
    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'instrument': self.instrument,
            'direction': self.direction,
            'entry_price': self.entry_price,
            'tp_price': self.tp_price,
            'sl_price': self.sl_price,
            'score': self.score,
            'reasoning': self.reasoning,
            'confidence': self.confidence,
            'r_r_ratio': self.r_r_ratio,
            'status': self.status
        }


class PremiumSignalScanner:
    """
    Scans for PREMIUM quality setups only
    Minimum score: 70/100
    Maximum per day: 10
    """
    
    def __init__(self, oanda_client, data_feed):
        self.oanda = oanda_client
        self.data_feed = data_feed
        self.min_quality_score = 70  # Only premium signals
        self.max_signals_per_day = 10
        self.pending_signals = []
        
        # Instruments to scan
        self.instruments = [
            'XAU_USD',  # Gold
            'EUR_USD', 'GBP_USD', 'USD_JPY',  # Major Forex
            'AUD_USD', 'USD_CAD', 'NZD_USD'   # Minor Forex
        ]
        
        logger.info("✅ Premium Signal Scanner initialized")
        logger.info(f"   Min score: {self.min_quality_score}/100")
        logger.info(f"   Max signals/day: {self.max_signals_per_day}")
    
    def calculate_quality_score(
        self,
        instrument: str,
        direction: str,
        price_data: Dict,
        indicators: Dict
    ) -> tuple[int, str]:
        """
        Calculate 0-100 quality score with reasoning
        """
        score = 0
        reasons = []
        
        # FACTOR 1: Trend Strength (25 points)
        ma_5 = indicators.get('ma_5', 0)
        ma_21 = indicators.get('ma_21', 0)
        ma_50 = indicators.get('ma_50', 0)
        
        if direction == 'BUY':
            if ma_5 > ma_21 > ma_50:
                score += 25
                reasons.append("Strong uptrend (all MAs aligned)")
            elif ma_5 > ma_21:
                score += 15
                reasons.append("Moderate uptrend")
        else:  # SELL
            if ma_5 < ma_21 < ma_50:
                score += 25
                reasons.append("Strong downtrend (all MAs aligned)")
            elif ma_5 < ma_21:
                score += 15
                reasons.append("Moderate downtrend")
        
        # FACTOR 2: Momentum (20 points)
        momentum = indicators.get('momentum', 0)
        if direction == 'BUY' and momentum > 0.008:
            score += 20
            reasons.append(f"Strong bullish momentum ({momentum*100:.2f}%)")
        elif direction == 'BUY' and momentum > 0.005:
            score += 12
            reasons.append(f"Good bullish momentum ({momentum*100:.2f}%)")
        elif direction == 'SELL' and momentum < -0.008:
            score += 20
            reasons.append(f"Strong bearish momentum ({momentum*100:.2f}%)")
        elif direction == 'SELL' and momentum < -0.005:
            score += 12
            reasons.append(f"Good bearish momentum ({momentum*100:.2f}%)")
        
        # FACTOR 3: Volatility (15 points)
        atr = indicators.get('atr', 0)
        atr_avg = indicators.get('atr_avg', 0)
        
        if atr > atr_avg * 1.2:
            score += 15
            reasons.append("High volatility (good movement potential)")
        elif atr > atr_avg:
            score += 10
            reasons.append("Above average volatility")
        
        # FACTOR 4: Market Structure (15 points)
        if indicators.get('higher_high') and direction == 'BUY':
            score += 15
            reasons.append("Making higher highs (bullish structure)")
        elif indicators.get('lower_low') and direction == 'SELL':
            score += 15
            reasons.append("Making lower lows (bearish structure)")
        
        # FACTOR 5: Session Timing (10 points)
        current_time = datetime.utcnow().time()
        london_start = time(8, 0)
        ny_end = time(21, 30)
        
        if london_start <= current_time <= ny_end:
            score += 10
            reasons.append("Prime trading session (London/NY)")
        
        # FACTOR 6: Risk/Reward (15 points)
        rr_ratio = indicators.get('rr_ratio', 0)
        if rr_ratio >= 3.0:
            score += 15
            reasons.append(f"Excellent R:R ({rr_ratio:.1f}:1)")
        elif rr_ratio >= 2.0:
            score += 10
            reasons.append(f"Good R:R ({rr_ratio:.1f}:1)")
        
        reasoning = " • " + "\n • ".join(reasons) if reasons else "No strong factors"
        
        return score, reasoning
    
    def scan_for_premium_signals(self) -> List[PremiumSignal]:
        """
        Scan all instruments for premium setups
        Returns list of signals with score >= 70
        """
        premium_signals = []
        
        logger.info(f"🔍 Scanning {len(self.instruments)} instruments for premium signals...")
        
        for instrument in self.instruments:
            try:
                # Get current price data
                prices = self.data_feed.get_latest_prices([instrument])
                if not prices or instrument not in prices:
                    continue
                
                price_data = prices[instrument]
                current_price = price_data.get('bid', 0)
                
                if current_price == 0:
                    continue
                
                # Get historical data for indicators
                history = self.oanda.get_candles(
                    instrument=instrument,
                    granularity='M15',
                    count=100
                )
                
                if not history or len(history) < 50:
                    continue
                
                # Calculate indicators
                closes = [float(c.get('mid', {}).get('c', 0)) for c in history]
                highs = [float(c.get('mid', {}).get('h', 0)) for c in history]
                lows = [float(c.get('mid', {}).get('l', 0)) for c in history]
                
                ma_5 = sum(closes[-5:]) / 5
                ma_21 = sum(closes[-21:]) / 21
                ma_50 = sum(closes[-50:]) / 50
                
                momentum = (closes[-1] - closes[-10]) / closes[-10]
                
                atr_values = [highs[i] - lows[i] for i in range(-20, 0)]
                atr = sum(atr_values) / len(atr_values)
                atr_avg = sum([highs[i] - lows[i] for i in range(-50, -20)]) / 30
                
                # Market structure
                recent_high = max(closes[-10:])
                prev_high = max(closes[-20:-10])
                higher_high = recent_high > prev_high
                
                recent_low = min(closes[-10:])
                prev_low = min(closes[-20:-10])
                lower_low = recent_low < prev_low
                
                # Check for BUY signal
                if ma_5 > ma_21 and momentum > 0.005:
                    tp = current_price + (atr * 3)
                    sl = current_price - (atr * 1.5)
                    rr_ratio = (tp - current_price) / (current_price - sl)
                    
                    indicators = {
                        'ma_5': ma_5,
                        'ma_21': ma_21,
                        'ma_50': ma_50,
                        'momentum': momentum,
                        'atr': atr,
                        'atr_avg': atr_avg,
                        'higher_high': higher_high,
                        'rr_ratio': rr_ratio
                    }
                    
                    score, reasoning = self.calculate_quality_score(
                        instrument, 'BUY', price_data, indicators
                    )
                    
                    if score >= self.min_quality_score:
                        signal = PremiumSignal(
                            id=f"{instrument}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                            timestamp=datetime.now(),
                            instrument=instrument,
                            direction='BUY',
                            entry_price=current_price,
                            tp_price=tp,
                            sl_price=sl,
                            score=score,
                            reasoning=reasoning,
                            confidence=score / 100.0,
                            r_r_ratio=rr_ratio
                        )
                        premium_signals.append(signal)
                        logger.info(f"   ✅ PREMIUM BUY: {instrument} (Score: {score}/100)")
                
                # Check for SELL signal
                if ma_5 < ma_21 and momentum < -0.005:
                    tp = current_price - (atr * 3)
                    sl = current_price + (atr * 1.5)
                    rr_ratio = (current_price - tp) / (sl - current_price)
                    
                    indicators = {
                        'ma_5': ma_5,
                        'ma_21': ma_21,
                        'ma_50': ma_50,
                        'momentum': momentum,
                        'atr': atr,
                        'atr_avg': atr_avg,
                        'lower_low': lower_low,
                        'rr_ratio': rr_ratio
                    }
                    
                    score, reasoning = self.calculate_quality_score(
                        instrument, 'SELL', price_data, indicators
                    )
                    
                    if score >= self.min_quality_score:
                        signal = PremiumSignal(
                            id=f"{instrument}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                            timestamp=datetime.now(),
                            instrument=instrument,
                            direction='SELL',
                            entry_price=current_price,
                            tp_price=tp,
                            sl_price=sl,
                            score=score,
                            reasoning=reasoning,
                            confidence=score / 100.0,
                            r_r_ratio=rr_ratio
                        )
                        premium_signals.append(signal)
                        logger.info(f"   ✅ PREMIUM SELL: {instrument} (Score: {score}/100)")
            
            except Exception as e:
                logger.error(f"Error scanning {instrument}: {e}")
                continue
        
        # Sort by score (highest first) and limit to max per day
        premium_signals.sort(key=lambda x: x.score, reverse=True)
        premium_signals = premium_signals[:self.max_signals_per_day]
        
        logger.info(f"✅ Found {len(premium_signals)} premium signals")
        
        return premium_signals
    
    def get_pending_signals(self) -> List[PremiumSignal]:
        """Get all pending signals awaiting approval"""
        return [s for s in self.pending_signals if s.status == 'pending']
    
    def approve_signal(self, signal_id: str) -> bool:
        """Approve a signal for execution"""
        for signal in self.pending_signals:
            if signal.id == signal_id and signal.status == 'pending':
                signal.status = 'approved'
                logger.info(f"✅ Signal approved: {signal_id}")
                return True
        return False
    
    def reject_signal(self, signal_id: str) -> bool:
        """Reject a signal"""
        for signal in self.pending_signals:
            if signal.id == signal_id and signal.status == 'pending':
                signal.status = 'rejected'
                logger.info(f"❌ Signal rejected: {signal_id}")
                return True
        return False


# Global instance
_premium_scanner = None

def get_premium_scanner(oanda_client=None, data_feed=None):
    """Get or create premium scanner instance"""
    global _premium_scanner
    if _premium_scanner is None and oanda_client and data_feed:
        _premium_scanner = PremiumSignalScanner(oanda_client, data_feed)
    return _premium_scanner


if __name__ == '__main__':
    # Test
    print("Premium Signal Scanner - Ready for integration")



