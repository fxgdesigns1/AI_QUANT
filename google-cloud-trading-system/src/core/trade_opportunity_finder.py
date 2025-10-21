#!/usr/bin/env python3
"""
TRADE OPPORTUNITY FINDER
AI finds opportunities → Shows you with context → You decide to execute

Features:
- Real-time opportunity scanning
- Full context (Trump DNA zones, quality, risk/reward)
- Pro/Con analysis
- Quality scoring (0-100)
- One-click execute or dismiss
- Learning from your choices
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class OpportunityQuality(Enum):
    """Opportunity quality levels"""
    EXCELLENT = "excellent"  # 80-100: Take it!
    GOOD = "good"           # 60-79: Strong opportunity
    MODERATE = "moderate"   # 40-59: Decent setup
    WEAK = "weak"          # 20-39: Risky
    POOR = "poor"          # 0-19: Skip


@dataclass
class TradeOpportunity:
    """
    A trade opportunity with full context for human decision-making
    """
    # Basic info
    id: str
    timestamp: datetime
    instrument: str
    direction: str  # BUY or SELL
    
    # Trump DNA Context
    at_sniper_zone: bool
    zone_type: str  # support, resistance, pivot
    zone_level: float
    distance_to_zone_pips: float
    
    # Entry/Exit
    suggested_entry: float
    fixed_stop_loss: float
    stop_loss_pips: float
    take_profit_stages: List[Dict]  # Multiple TPs
    risk_reward_ratio: float
    
    # Quality Analysis
    quality_score: int  # 0-100
    quality_level: OpportunityQuality
    confluence_factors: Dict[str, bool]  # Which factors align
    regime: str  # TRENDING, RANGING, VOLATILE
    
    # Context
    current_price: float
    daily_target_progress: float  # % of daily target achieved
    trades_today: int
    max_trades_remaining: int
    
    # Decision Support
    pros: List[str]  # Why you SHOULD take this
    cons: List[str]  # Why you SHOULDN'T take this
    recommendation: str  # STRONG BUY, BUY, HOLD, AVOID
    
    # News/Events
    upcoming_news: List[Dict]  # Next 2 hours
    news_risk: str  # LOW, MEDIUM, HIGH
    
    # Strategy
    strategy_name: str
    expected_win_rate: float
    expected_profit: float  # Estimated $ if wins
    expected_loss: float    # Estimated $ if loses
    
    # Actions
    approved: bool = False
    executed: bool = False
    dismissed: bool = False
    dismiss_reason: str = ""


class TradeOpportunityFinder:
    """
    Finds trade opportunities and presents them for manual approval
    You see the opportunity → You decide → You execute
    """
    
    def __init__(self):
        self.name = "AI Trade Opportunity Finder"
        self.opportunities = []  # Active opportunities
        self.approved_trades = []
        self.dismissed_trades = []
        
        # Learning
        self.user_preferences = {
            'min_quality_score': 60,  # You prefer 60+ quality
            'max_risk_pips': 15,      # Max 15 pip stops
            'preferred_times': ['13:00-17:00'],  # London/NY overlap
            'avoid_news_buffer': 30,  # 30 min before news
        }
        
        logger.info("✅ Trade Opportunity Finder initialized (AI-Assisted Manual Trading)")
    
    def find_opportunities(self, strategies: List, market_data: Dict) -> List[TradeOpportunity]:
        """
        Scan all strategies and find trade opportunities
        Returns list of opportunities for you to review
        """
        
        opportunities = []
        
        for strategy in strategies:
            for instrument in strategy.instruments:
                # Get strategy's analysis
                signal = strategy.analyze_market(instrument, market_data[instrument])
                
                if signal:
                    # Convert signal to opportunity with full context
                    opportunity = self._create_opportunity(signal, strategy)
                    opportunities.append(opportunity)
        
        # Sort by quality (best first)
        opportunities.sort(key=lambda x: x.quality_score, reverse=True)
        
        self.opportunities = opportunities
        logger.info(f"🎯 Found {len(opportunities)} trade opportunities")
        
        return opportunities
    
    def _create_opportunity(self, signal, strategy) -> TradeOpportunity:
        """Create detailed opportunity card from signal"""
        
        # Calculate quality score (0-100)
        quality_score = self._calculate_quality_score(signal, strategy)
        quality_level = self._get_quality_level(quality_score)
        
        # Analyze pros/cons
        pros, cons = self._analyze_pros_cons(signal, strategy, quality_score)
        
        # Get recommendation
        recommendation = self._get_recommendation(quality_score, pros, cons)
        
        # Calculate R:R
        entry = signal.entry_price
        stop = signal.stop_loss
        tp = signal.take_profit
        
        risk_pips = abs(entry - stop) * (10000 if 'JPY' not in signal.instrument else 100)
        reward_pips = abs(tp - entry) * (10000 if 'JPY' not in signal.instrument else 100)
        risk_reward = reward_pips / risk_pips if risk_pips > 0 else 0
        
        # Get Trump DNA context
        trump_dna = strategy.trump_dna if hasattr(strategy, 'trump_dna') else None
        
        opportunity = TradeOpportunity(
            id=f"{signal.instrument}_{datetime.now().strftime('%H%M%S')}",
            timestamp=datetime.now(),
            instrument=signal.instrument,
            direction="BUY" if signal.side.name == "BUY" else "SELL",
            
            # Trump DNA
            at_sniper_zone=signal.metadata.get('sniper_zone') is not None,
            zone_type=signal.metadata.get('sniper_zone', {}).get('type', 'none'),
            zone_level=signal.metadata.get('sniper_zone', {}).get('level', 0),
            distance_to_zone_pips=signal.metadata.get('distance_to_zone', 0),
            
            # Entry/Exit
            suggested_entry=entry,
            fixed_stop_loss=stop,
            stop_loss_pips=risk_pips,
            take_profit_stages=signal.metadata.get('tp_stages', []),
            risk_reward_ratio=risk_reward,
            
            # Quality
            quality_score=quality_score,
            quality_level=quality_level,
            confluence_factors=signal.metadata.get('confluence_factors', {}),
            regime=signal.metadata.get('regime', 'UNKNOWN'),
            
            # Context
            current_price=entry,
            daily_target_progress=trump_dna.profit_today / trump_dna.weekly_plan.daily_targets.get(datetime.now().strftime('%A'), 1) * 100 if trump_dna else 0,
            trades_today=trump_dna.trades_today if trump_dna else 0,
            max_trades_remaining=trump_dna.weekly_plan.max_trades_per_day - trump_dna.trades_today if trump_dna else 10,
            
            # Decision Support
            pros=pros,
            cons=cons,
            recommendation=recommendation,
            
            # News
            upcoming_news=self._get_upcoming_news(),
            news_risk=self._assess_news_risk(),
            
            # Strategy
            strategy_name=strategy.name,
            expected_win_rate=strategy.expected_win_rate if hasattr(strategy, 'expected_win_rate') else 0.60,
            expected_profit=reward_pips * 10,  # $10 per pip estimate
            expected_loss=risk_pips * 10,
        )
        
        return opportunity
    
    def _calculate_quality_score(self, signal, strategy) -> int:
        """Calculate 0-100 quality score"""
        
        score = 0
        
        # Base confidence (0-40 points)
        score += signal.confidence * 40
        
        # At sniper zone (0-20 points)
        if signal.metadata.get('sniper_zone'):
            score += 20
        
        # Good R:R (0-15 points)
        entry = signal.entry_price
        stop = signal.stop_loss
        tp = signal.take_profit
        rr = abs(tp - entry) / abs(entry - stop) if abs(entry - stop) > 0 else 0
        if rr >= 2.0:
            score += 15
        elif rr >= 1.5:
            score += 10
        elif rr >= 1.0:
            score += 5
        
        # Session quality (0-10 points)
        hour = datetime.now().hour
        if 13 <= hour < 17:  # London/NY overlap
            score += 10
        elif 7 <= hour < 21:  # London or NY
            score += 5
        
        # Low news risk (0-10 points)
        if self._assess_news_risk() == "LOW":
            score += 10
        elif self._assess_news_risk() == "MEDIUM":
            score += 5
        
        # Daily target not hit (0-5 points)
        if hasattr(strategy, 'trump_dna'):
            today = datetime.now().strftime('%A')
            daily_target = strategy.trump_dna.weekly_plan.daily_targets.get(today, 0)
            if strategy.trump_dna.profit_today < daily_target:
                score += 5
        
        return min(100, int(score))
    
    def _get_quality_level(self, score: int) -> OpportunityQuality:
        """Convert score to quality level"""
        if score >= 80:
            return OpportunityQuality.EXCELLENT
        elif score >= 60:
            return OpportunityQuality.GOOD
        elif score >= 40:
            return OpportunityQuality.MODERATE
        elif score >= 20:
            return OpportunityQuality.WEAK
        else:
            return OpportunityQuality.POOR
    
    def _analyze_pros_cons(self, signal, strategy, quality_score) -> tuple[List[str], List[str]]:
        """Analyze why to take or skip this trade"""
        
        pros = []
        cons = []
        
        # Sniper zone
        if signal.metadata.get('sniper_zone'):
            pros.append(f"✅ At key {signal.metadata['sniper_zone']['type']} level")
        else:
            cons.append("⚠️ Not at sniper zone (random entry)")
        
        # Quality score
        if quality_score >= 70:
            pros.append(f"✅ High quality score ({quality_score}/100)")
        elif quality_score < 50:
            cons.append(f"⚠️ Low quality score ({quality_score}/100)")
        
        # Confluence
        confluence_count = len([f for f in signal.metadata.get('confluence_factors', {}).values() if f])
        if confluence_count >= 3:
            pros.append(f"✅ {confluence_count} factors aligned")
        elif confluence_count < 2:
            cons.append(f"⚠️ Only {confluence_count} factor(s) aligned")
        
        # Session
        hour = datetime.now().hour
        if 13 <= hour < 17:
            pros.append("✅ Prime time (London/NY overlap)")
        elif hour < 7 or hour > 21:
            cons.append("⚠️ Outside main sessions")
        
        # News
        if self._assess_news_risk() == "HIGH":
            cons.append("⚠️ High impact news in next 30 min")
        elif self._assess_news_risk() == "LOW":
            pros.append("✅ No major news upcoming")
        
        # Regime
        regime = signal.metadata.get('regime', 'UNKNOWN')
        if regime == "TRENDING" and quality_score >= 60:
            pros.append("✅ Trending market (favorable)")
        elif regime == "RANGING":
            cons.append("⚠️ Ranging market (harder to profit)")
        
        # Risk/Reward
        entry = signal.entry_price
        stop = signal.stop_loss
        tp = signal.take_profit
        rr = abs(tp - entry) / abs(entry - stop) if abs(entry - stop) > 0 else 0
        if rr >= 2.0:
            pros.append(f"✅ Excellent R:R ({rr:.1f}:1)")
        elif rr < 1.5:
            cons.append(f"⚠️ Poor R:R ({rr:.1f}:1)")
        
        return pros, cons
    
    def _get_recommendation(self, quality_score: int, pros: List[str], cons: List[str]) -> str:
        """Get recommendation based on quality and pros/cons"""
        
        if quality_score >= 75 and len(pros) >= 4:
            return "STRONG BUY"
        elif quality_score >= 60 and len(pros) >= 3:
            return "BUY"
        elif quality_score >= 40 and len(cons) <= 2:
            return "CONSIDER"
        else:
            return "AVOID"
    
    def _get_upcoming_news(self) -> List[Dict]:
        """Get news events in next 2 hours"""
        # Simplified - would integrate with economic calendar
        return [
            {'time': '14:30', 'event': 'US GDP', 'impact': 'HIGH'},
        ]
    
    def _assess_news_risk(self) -> str:
        """Assess news risk level"""
        # Simplified - would check actual calendar
        now = datetime.now()
        hour = now.hour
        minute = now.minute
        
        # High risk: 30 min before major news (typically 13:30, 14:30)
        if (hour == 13 and minute >= 0) or (hour == 14 and minute >= 0):
            return "MEDIUM"
        
        return "LOW"
    
    def approve_opportunity(self, opportunity_id: str, user_notes: str = ""):
        """User approves an opportunity - ready to execute"""
        
        opp = next((o for o in self.opportunities if o.id == opportunity_id), None)
        if opp:
            opp.approved = True
            self.approved_trades.append(opp)
            logger.info(f"✅ Opportunity approved: {opp.instrument} {opp.direction}")
            return True
        return False
    
    def dismiss_opportunity(self, opportunity_id: str, reason: str = ""):
        """User dismisses an opportunity"""
        
        opp = next((o for o in self.opportunities if o.id == opportunity_id), None)
        if opp:
            opp.dismissed = True
            opp.dismiss_reason = reason
            self.dismissed_trades.append(opp)
            logger.info(f"❌ Opportunity dismissed: {opp.instrument} - Reason: {reason}")
            
            # Learn from dismissal
            self._learn_from_dismissal(opp, reason)
            return True
        return False
    
    def _learn_from_dismissal(self, opp: TradeOpportunity, reason: str):
        """Learn from user's dismissal to improve future recommendations"""
        
        # If user consistently dismisses low quality, raise threshold
        if "low quality" in reason.lower() and opp.quality_score < 70:
            self.user_preferences['min_quality_score'] = max(
                self.user_preferences['min_quality_score'],
                opp.quality_score + 5
            )
            logger.info(f"📚 Learning: Raised min quality to {self.user_preferences['min_quality_score']}")
        
        # If user avoids wide stops
        if "stop too wide" in reason.lower():
            self.user_preferences['max_risk_pips'] = min(
                self.user_preferences['max_risk_pips'],
                opp.stop_loss_pips - 2
            )
            logger.info(f"📚 Learning: Reduced max risk to {self.user_preferences['max_risk_pips']} pips")
    
    def get_active_opportunities(self) -> List[TradeOpportunity]:
        """Get opportunities that haven't been approved or dismissed"""
        return [o for o in self.opportunities if not o.approved and not o.dismissed]
    
    def get_user_stats(self) -> Dict:
        """Get stats on user's decision-making"""
        
        total = len(self.approved_trades) + len(self.dismissed_trades)
        if total == 0:
            return {}
        
        approval_rate = len(self.approved_trades) / total * 100
        avg_quality_approved = np.mean([o.quality_score for o in self.approved_trades]) if self.approved_trades else 0
        
        return {
            'total_opportunities_shown': total,
            'approved': len(self.approved_trades),
            'dismissed': len(self.dismissed_trades),
            'approval_rate': approval_rate,
            'avg_quality_approved': avg_quality_approved,
            'preferences': self.user_preferences
        }


# Global instance
_opportunity_finder = None

def get_opportunity_finder() -> TradeOpportunityFinder:
    """Get opportunity finder instance"""
    global _opportunity_finder
    if _opportunity_finder is None:
        _opportunity_finder = TradeOpportunityFinder()
    return _opportunity_finder



