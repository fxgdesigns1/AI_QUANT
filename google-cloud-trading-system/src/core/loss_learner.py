#!/usr/bin/env python3
"""
Loss Learning System - Learn from past mistakes to improve future trades
Tracks losing conditions and adjusts risk (NEVER relaxes entry thresholds)
"""

import logging
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LossLearner:
    """
    Learn from losses to improve risk management
    - Tracks which conditions led to losses
    - Builds failure pattern database
    - Adjusts position sizing after losses (NEVER relaxes entry criteria)
    - Independent per-strategy tracking
    """
    
    def __init__(self, strategy_name: str):
        """Initialize loss learner for a specific strategy"""
        self.strategy_name = strategy_name
        self.data_dir = os.path.join(
            os.path.dirname(__file__), '../../strategy_learning_data'
        )
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.data_file = os.path.join(
            self.data_dir, f'{strategy_name}_losses.json'
        )
        
        # Load existing data
        self.loss_history = self._load_loss_history()
        
        # Performance tracking
        self.recent_performance = {
            'last_10_trades': [],
            'last_10_win_rate': 0.0,
            'consecutive_losses': 0,
            'total_trades': 0,
            'total_wins': 0,
            'total_losses': 0
        }
        
        logger.info(f"✅ Loss Learner initialized for {strategy_name}")
        logger.info(f"📊 Loaded {len(self.loss_history)} historical losses")
    
    def _load_loss_history(self) -> List[Dict]:
        """Load historical loss data from file"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load loss history: {e}")
                return []
        return []
    
    def _save_loss_history(self):
        """Save loss history to file"""
        try:
            with open(self.data_file, 'w') as f:
                json.dump(self.loss_history, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Could not save loss history: {e}")
    
    def record_loss(
        self,
        instrument: str,
        regime: str,
        adx: float,
        momentum: float,
        volume: float,
        pnl: float,
        conditions: Dict
    ):
        """
        Record a losing trade to learn from
        
        Args:
            instrument: Trading instrument (e.g., 'EUR_USD')
            regime: Market regime ('TRENDING', 'RANGING', 'CHOPPY')
            adx: ADX value at entry
            momentum: Momentum value at entry
            volume: Volume indicator at entry
            pnl: Profit/loss (negative)
            conditions: Additional conditions dict
        """
        loss_record = {
            'timestamp': datetime.now().isoformat(),
            'instrument': instrument,
            'regime': regime,
            'adx': adx,
            'momentum': momentum,
            'volume': volume,
            'pnl': pnl,
            'conditions': conditions
        }
        
        self.loss_history.append(loss_record)
        
        # Keep only last 200 losses (don't grow forever)
        if len(self.loss_history) > 200:
            self.loss_history = self.loss_history[-200:]
        
        self._save_loss_history()
        
        # Update performance tracking
        self.recent_performance['consecutive_losses'] += 1
        self.recent_performance['total_losses'] += 1
        self.recent_performance['total_trades'] += 1
        self.recent_performance['last_10_trades'].append('LOSS')
        if len(self.recent_performance['last_10_trades']) > 10:
            self.recent_performance['last_10_trades'].pop(0)
        
        # Calculate win rate
        wins = self.recent_performance['last_10_trades'].count('WIN')
        total = len(self.recent_performance['last_10_trades'])
        self.recent_performance['last_10_win_rate'] = wins / total if total > 0 else 0.0
        
        logger.info(f"📉 Recorded loss: {instrument} in {regime} market, PnL: ${pnl:.2f}")
        logger.info(f"   Consecutive losses: {self.recent_performance['consecutive_losses']}")
    
    def record_win(self, instrument: str, pnl: float):
        """Record a winning trade"""
        self.recent_performance['consecutive_losses'] = 0
        self.recent_performance['total_wins'] += 1
        self.recent_performance['total_trades'] += 1
        self.recent_performance['last_10_trades'].append('WIN')
        if len(self.recent_performance['last_10_trades']) > 10:
            self.recent_performance['last_10_trades'].pop(0)
        
        # Calculate win rate
        wins = self.recent_performance['last_10_trades'].count('WIN')
        total = len(self.recent_performance['last_10_trades'])
        self.recent_performance['last_10_win_rate'] = wins / total if total > 0 else 0.0
        
        logger.info(f"📈 Recorded win: {instrument}, PnL: ${pnl:.2f}")
    
    def get_risk_adjustment(self, instrument: str, regime: str) -> float:
        """
        Get risk multiplier based on recent performance
        
        Returns: Float between 0.5-1.0
        - 1.0 = full size (good performance)
        - 0.75 = 75% size (moderate losses)
        - 0.5 = 50% size (significant losses)
        
        IMPORTANT: This REDUCES risk after losses, NEVER increases it
        """
        # Base multiplier
        multiplier = 1.0
        
        # Reduce after consecutive losses
        if self.recent_performance['consecutive_losses'] >= 5:
            multiplier = 0.5  # Cut size in half after 5 losses
            logger.warning(f"⚠️ Risk reduced to 50% due to {self.recent_performance['consecutive_losses']} consecutive losses")
        elif self.recent_performance['consecutive_losses'] >= 3:
            multiplier = 0.75  # 75% size after 3 losses
            logger.warning(f"⚠️ Risk reduced to 75% due to {self.recent_performance['consecutive_losses']} consecutive losses")
        
        # Also check win rate in last 10 trades
        if self.recent_performance['last_10_win_rate'] < 0.30:  # Below 30% WR
            multiplier = min(multiplier, 0.5)
            logger.warning(f"⚠️ Risk reduced to 50% due to low win rate: {self.recent_performance['last_10_win_rate']:.1%}")
        
        # Check instrument-specific losses
        instrument_losses = self._get_instrument_loss_count(instrument, days=7)
        if instrument_losses >= 3:
            multiplier = min(multiplier, 0.75)
            logger.warning(f"⚠️ Risk reduced to 75% for {instrument} due to {instrument_losses} losses in last 7 days")
        
        # Check regime-specific losses
        regime_losses = self._get_regime_loss_count(regime, days=7)
        if regime_losses >= 5:
            multiplier = min(multiplier, 0.75)
            logger.warning(f"⚠️ Risk reduced to 75% in {regime} regime due to {regime_losses} losses in last 7 days")
        
        return multiplier
    
    def _get_instrument_loss_count(self, instrument: str, days: int = 7) -> int:
        """Count losses for specific instrument in recent days"""
        cutoff = datetime.now() - timedelta(days=days)
        count = 0
        for loss in self.loss_history:
            try:
                loss_time = datetime.fromisoformat(loss['timestamp'])
                if loss_time >= cutoff and loss['instrument'] == instrument:
                    count += 1
            except:
                continue
        return count
    
    def _get_regime_loss_count(self, regime: str, days: int = 7) -> int:
        """Count losses in specific regime in recent days"""
        cutoff = datetime.now() - timedelta(days=days)
        count = 0
        for loss in self.loss_history:
            try:
                loss_time = datetime.fromisoformat(loss['timestamp'])
                if loss_time >= cutoff and loss.get('regime') == regime:
                    count += 1
            except:
                continue
        return count
    
    def is_failure_pattern(self, conditions: Dict) -> bool:
        """
        Check if current conditions are similar to past failures
        
        Args:
            conditions: Dict with current market conditions
                - instrument: str
                - regime: str
                - adx: float
                - momentum: float
                - volume: float
        
        Returns: True if similar to 3+ past losses
        """
        if len(self.loss_history) < 3:
            return False  # Not enough data
        
        similar_count = 0
        
        for loss in self.loss_history[-30:]:  # Check last 30 losses
            similarity_score = 0
            
            # Check instrument match
            if loss.get('instrument') == conditions.get('instrument'):
                similarity_score += 1
            
            # Check regime match
            if loss.get('regime') == conditions.get('regime'):
                similarity_score += 1
            
            # Check ADX similarity (within 20%)
            if 'adx' in loss and 'adx' in conditions:
                adx_diff = abs(loss['adx'] - conditions['adx']) / max(loss['adx'], 0.01)
                if adx_diff < 0.20:  # Within 20%
                    similarity_score += 1
            
            # Check momentum similarity (within 30%)
            if 'momentum' in loss and 'momentum' in conditions:
                mom_diff = abs(loss['momentum'] - conditions['momentum']) / max(abs(loss['momentum']), 0.0001)
                if mom_diff < 0.30:  # Within 30%
                    similarity_score += 1
            
            # If 3+ factors match, it's a similar pattern
            if similarity_score >= 3:
                similar_count += 1
        
        if similar_count >= 3:
            logger.warning(f"🚫 Failure pattern detected: {similar_count} similar past losses")
            return True
        
        return False
    
    def get_avoidance_list(self, days: int = 14) -> List[Dict]:
        """
        Get list of conditions to avoid based on recent losses
        
        Returns: List of dicts with problematic conditions
        """
        cutoff = datetime.now() - timedelta(days=days)
        recent_losses = []
        
        for loss in self.loss_history:
            try:
                loss_time = datetime.fromisoformat(loss['timestamp'])
                if loss_time >= cutoff:
                    recent_losses.append(loss)
            except:
                continue
        
        if len(recent_losses) < 5:
            return []  # Not enough data
        
        # Analyze patterns
        avoidance_patterns = []
        
        # Group by instrument
        instrument_losses = defaultdict(int)
        for loss in recent_losses:
            instrument_losses[loss.get('instrument', 'UNKNOWN')] += 1
        
        # Avoid instruments with 4+ losses
        for instrument, count in instrument_losses.items():
            if count >= 4:
                avoidance_patterns.append({
                    'type': 'INSTRUMENT',
                    'value': instrument,
                    'reason': f'{count} losses in {days} days',
                    'severity': 'HIGH'
                })
        
        # Group by regime
        regime_losses = defaultdict(int)
        for loss in recent_losses:
            regime_losses[loss.get('regime', 'UNKNOWN')] += 1
        
        # Avoid regimes with 6+ losses
        for regime, count in regime_losses.items():
            if count >= 6:
                avoidance_patterns.append({
                    'type': 'REGIME',
                    'value': regime,
                    'reason': f'{count} losses in {days} days',
                    'severity': 'MEDIUM'
                })
        
        return avoidance_patterns
    
    def get_performance_summary(self) -> Dict:
        """Get performance summary for reporting"""
        return {
            'strategy': self.strategy_name,
            'total_trades': self.recent_performance['total_trades'],
            'total_wins': self.recent_performance['total_wins'],
            'total_losses': self.recent_performance['total_losses'],
            'overall_win_rate': (
                self.recent_performance['total_wins'] / self.recent_performance['total_trades']
                if self.recent_performance['total_trades'] > 0 else 0.0
            ),
            'last_10_win_rate': self.recent_performance['last_10_win_rate'],
            'consecutive_losses': self.recent_performance['consecutive_losses'],
            'historical_losses_tracked': len(self.loss_history),
            'avoidance_patterns': self.get_avoidance_list()
        }


# Global instances (one per strategy)
_loss_learners: Dict[str, LossLearner] = {}


def get_loss_learner(strategy_name: str) -> LossLearner:
    """Get or create loss learner instance for a strategy"""
    global _loss_learners
    if strategy_name not in _loss_learners:
        _loss_learners[strategy_name] = LossLearner(strategy_name)
    return _loss_learners[strategy_name]

