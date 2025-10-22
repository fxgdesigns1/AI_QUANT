#!/usr/bin/env python3
"""
Brutal Honesty Reporter - Tell the truth about market conditions and signals
No sugar-coating, no false confidence, just honest assessment
"""

import logging
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HonestyReporter:
    """
    Provides brutal honesty about trading decisions:
    - Detailed rejection logging with exact scores
    - Market condition alerts (good/poor/no setups)
    - Realistic win probability estimates
    - End-of-day honest assessment
    """
    
    def __init__(self, strategy_name: str):
        """Initialize honesty reporter for a specific strategy"""
        self.strategy_name = strategy_name
        self.log_dir = os.path.join(
            os.path.dirname(__file__), '../../strategy_honesty_logs'
        )
        os.makedirs(self.log_dir, exist_ok=True)
        
        self.rejection_log_file = os.path.join(
            self.log_dir, f'{strategy_name}_rejections_{datetime.now().strftime("%Y%m%d")}.jsonl'
        )
        
        # Tracking
        self.today_rejections = []
        self.today_signals = []
        self.last_alert_time = None
        
        # Historical win rates by regime (updated as we learn)
        self.historical_win_rates = self._load_win_rate_history()
        
        logger.info(f"✅ Honesty Reporter initialized for {strategy_name}")
    
    def _load_win_rate_history(self) -> Dict:
        """Load historical win rates by regime/instrument"""
        history_file = os.path.join(self.log_dir, f'{self.strategy_name}_win_rates.json')
        if os.path.exists(history_file):
            try:
                with open(history_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        # Default estimates based on market regime
        return {
            'TRENDING': 0.60,   # 60% WR in trending markets
            'RANGING': 0.45,    # 45% WR in ranging markets
            'CHOPPY': 0.30,     # 30% WR in choppy markets
            'UNKNOWN': 0.40     # 40% WR when uncertain
        }
    
    def _save_win_rate_history(self):
        """Save win rate history"""
        history_file = os.path.join(self.log_dir, f'{self.strategy_name}_win_rates.json')
        try:
            with open(history_file, 'w') as f:
                json.dump(self.historical_win_rates, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save win rate history: {e}")
    
    def log_rejection(
        self,
        instrument: str,
        reasons: List[str],
        scores: Dict[str, Dict],
        conditions: Optional[Dict] = None
    ):
        """
        Log a rejected signal with brutal honesty
        
        Args:
            instrument: Trading instrument
            reasons: List of rejection reasons
            scores: Dict of component scores {'ADX': {'value': 22, 'required': 25, 'passed': False}}
            conditions: Additional market conditions
        """
        rejection_record = {
            'timestamp': datetime.now().isoformat(),
            'instrument': instrument,
            'reasons': reasons,
            'scores': scores,
            'conditions': conditions or {}
        }
        
        self.today_rejections.append(rejection_record)
        
        # Append to JSONL file (one JSON per line)
        try:
            with open(self.rejection_log_file, 'a') as f:
                f.write(json.dumps(rejection_record) + '\n')
        except Exception as e:
            logger.error(f"Could not write rejection log: {e}")
        
        # Log detailed breakdown
        logger.info(f"🚫 REJECTED: {instrument}")
        for reason in reasons:
            logger.info(f"   ❌ {reason}")
        
        # Log component scores
        for component, data in scores.items():
            if isinstance(data, dict):
                value = data.get('value', 'N/A')
                required = data.get('required', 'N/A')
                passed = data.get('passed', False)
                status = "✓" if passed else "✗"
                logger.info(f"   {status} {component}: {value} (required: {required})")
    
    def send_market_outlook_alert(
        self,
        regime: str,
        quality_conditions: str,
        expected_setups: str,
        telegram_enabled: bool = True
    ):
        """
        Send honest market outlook alert
        
        Args:
            regime: Current market regime
            quality_conditions: 'GOOD', 'POOR', 'TERRIBLE'
            expected_setups: 'Many', 'Few', 'None'
            telegram_enabled: Whether to send Telegram alert
        """
        # Don't spam - only send once per 4 hours
        if self.last_alert_time:
            time_since_last = datetime.now() - self.last_alert_time
            if time_since_last < timedelta(hours=4):
                return
        
        self.last_alert_time = datetime.now()
        
        # Create honest message
        if quality_conditions == 'GOOD':
            emoji = "✅"
            message = f"{emoji} **GOOD SETUP CONDITIONS**\n"
            message += f"Market: {regime}\n"
            message += f"Expected setups: {expected_setups}\n"
            message += f"Strategy: {self.strategy_name}\n"
            message += "Monitoring for quality entries..."
        elif quality_conditions == 'POOR':
            emoji = "⚠️"
            message = f"{emoji} **POOR SETUP CONDITIONS**\n"
            message += f"Market: {regime}\n"
            message += f"Expected setups: {expected_setups}\n"
            message += f"Strategy: {self.strategy_name}\n"
            message += "Low probability trades - staying cautious"
        else:  # TERRIBLE
            emoji = "🚫"
            message = f"{emoji} **NO GOOD SETUPS TODAY**\n"
            message += f"Market: {regime} (unfavorable)\n"
            message += f"Expected setups: {expected_setups}\n"
            message += f"Strategy: {self.strategy_name}\n"
            message += "Better to wait - capital preservation mode"
        
        logger.info(message)
        
        if telegram_enabled:
            self._send_telegram(message)
    
    def calculate_win_probability(
        self,
        instrument: str,
        regime: str,
        quality_score: float,
        adx: Optional[float] = None,
        momentum: Optional[float] = None
    ) -> float:
        """
        Calculate realistic win probability for a trade
        
        Args:
            instrument: Trading instrument
            regime: Market regime
            quality_score: Quality score (0-100)
            adx: ADX value
            momentum: Momentum value
        
        Returns: Win probability (0.0-1.0)
        """
        # Start with base win rate for regime
        base_wr = self.historical_win_rates.get(regime, 0.40)
        
        # Adjust based on quality score (normalized to 0-100)
        quality_factor = (quality_score / 100) * 0.3  # Up to +30% for perfect quality
        
        # Adjust based on ADX (strong trend = better odds)
        adx_factor = 0.0
        if adx is not None:
            if adx >= 40:  # Very strong trend
                adx_factor = 0.10
            elif adx >= 30:  # Strong trend
                adx_factor = 0.05
            elif adx < 15:  # Weak trend (reduces probability)
                adx_factor = -0.10
        
        # Adjust based on momentum strength
        momentum_factor = 0.0
        if momentum is not None:
            if abs(momentum) >= 0.015:  # Strong momentum (1.5%+)
                momentum_factor = 0.10
            elif abs(momentum) >= 0.010:  # Good momentum (1.0%+)
                momentum_factor = 0.05
            elif abs(momentum) < 0.003:  # Weak momentum
                momentum_factor = -0.05
        
        # Calculate final probability
        win_prob = base_wr + quality_factor + adx_factor + momentum_factor
        
        # Clamp to realistic range (15% - 75%)
        win_prob = max(0.15, min(0.75, win_prob))
        
        logger.info(f"📊 Win Probability: {win_prob:.1%} ({regime} regime, quality={quality_score:.0f})")
        
        return win_prob
    
    def generate_daily_report(
        self,
        trades_taken: int,
        trades_rejected: int,
        market_conditions: Dict,
        performance: Optional[Dict] = None
    ) -> str:
        """
        Generate end-of-day honest assessment
        
        Args:
            trades_taken: Number of trades executed
            trades_rejected: Number of signals rejected
            market_conditions: Dict with regime, quality, etc.
            performance: Optional dict with win/loss results
        
        Returns: Report string
        """
        report = []
        report.append("=" * 60)
        report.append(f"DAILY HONESTY REPORT - {self.strategy_name}")
        report.append(f"Date: {datetime.now().strftime('%Y-%m-%d')}")
        report.append("=" * 60)
        report.append("")
        
        # Trades summary
        report.append("TRADING ACTIVITY:")
        report.append(f"  Signals evaluated: {trades_taken + trades_rejected}")
        report.append(f"  Trades taken: {trades_taken}")
        report.append(f"  Signals rejected: {trades_rejected}")
        
        if trades_taken == 0:
            report.append("")
            report.append("✅ CORRECT DECISION: Zero trades taken")
            report.append("   No quality setups met our strict criteria")
            report.append("   Capital preserved - better than forcing bad trades")
        else:
            rejection_rate = trades_rejected / (trades_taken + trades_rejected) * 100 if (trades_taken + trades_rejected) > 0 else 0
            report.append(f"  Rejection rate: {rejection_rate:.1f}%")
        
        report.append("")
        
        # Market conditions
        report.append("MARKET CONDITIONS:")
        regime = market_conditions.get('regime', 'UNKNOWN')
        report.append(f"  Regime: {regime}")
        report.append(f"  Quality: {market_conditions.get('quality', 'UNKNOWN')}")
        
        if regime == 'CHOPPY':
            report.append("  ⚠️ Choppy market - Low win rate expected")
        elif regime == 'RANGING':
            report.append("  ⚠️ Ranging market - Selective entries only")
        elif regime == 'TRENDING':
            report.append("  ✅ Trending market - Good conditions")
        
        report.append("")
        
        # Performance (if provided)
        if performance:
            report.append("PERFORMANCE:")
            wins = performance.get('wins', 0)
            losses = performance.get('losses', 0)
            total = wins + losses
            
            if total > 0:
                win_rate = wins / total
                expected_wr = self.historical_win_rates.get(regime, 0.40)
                
                report.append(f"  Trades completed: {total}")
                report.append(f"  Win rate: {win_rate:.1%} (expected: {expected_wr:.1%})")
                
                if win_rate >= expected_wr:
                    report.append(f"  ✅ MEETING EXPECTATIONS")
                else:
                    report.append(f"  ⚠️ BELOW EXPECTATIONS")
                    report.append(f"  Review rejection logs for improvement")
            else:
                report.append("  No completed trades yet")
        
        report.append("")
        
        # Top rejection reasons
        if self.today_rejections:
            report.append("TOP REJECTION REASONS:")
            reasons_count = defaultdict(int)
            for rejection in self.today_rejections:
                for reason in rejection['reasons']:
                    reasons_count[reason] += 1
            
            sorted_reasons = sorted(reasons_count.items(), key=lambda x: x[1], reverse=True)
            for reason, count in sorted_reasons[:5]:  # Top 5
                report.append(f"  • {reason}: {count} times")
        
        report.append("")
        report.append("=" * 60)
        
        full_report = "\n".join(report)
        logger.info(f"\n{full_report}")
        
        return full_report
    
    def update_win_rate(self, regime: str, actual_wr: float, trades_count: int):
        """
        Update historical win rate based on actual results
        
        Args:
            regime: Market regime
            actual_wr: Actual win rate achieved
            trades_count: Number of trades in sample
        """
        if trades_count < 10:
            return  # Need at least 10 trades for meaningful update
        
        current_wr = self.historical_win_rates.get(regime, 0.40)
        
        # Weighted average (give more weight to larger samples)
        weight = min(trades_count / 50, 0.3)  # Max 30% weight for new data
        updated_wr = (current_wr * (1 - weight)) + (actual_wr * weight)
        
        self.historical_win_rates[regime] = updated_wr
        self._save_win_rate_history()
        
        logger.info(f"📈 Updated {regime} win rate: {current_wr:.1%} → {updated_wr:.1%} (n={trades_count})")
    
    def _send_telegram(self, message: str):
        """Send Telegram alert (if configured)"""
        try:
            import os
            import requests
            
            bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '7248728383:AAEE7lkAAIUXBcK9iTPR5NIeTq3Aqbyx6IU')
            chat_id = os.environ.get('TELEGRAM_CHAT_ID', '6100678501')
            
            if bot_token and chat_id:
                url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
                data = {
                    'chat_id': chat_id,
                    'text': message,
                    'parse_mode': 'Markdown'
                }
                requests.post(url, data=data, timeout=10)
        except Exception as e:
            logger.warning(f"Could not send Telegram alert: {e}")
    
    def get_rejection_summary(self) -> Dict:
        """Get summary of today's rejections"""
        reasons_count = defaultdict(int)
        instruments_rejected = defaultdict(int)
        
        for rejection in self.today_rejections:
            for reason in rejection['reasons']:
                reasons_count[reason] += 1
            instruments_rejected[rejection['instrument']] += 1
        
        return {
            'total_rejections': len(self.today_rejections),
            'top_reasons': dict(sorted(reasons_count.items(), key=lambda x: x[1], reverse=True)[:5]),
            'instruments_rejected': dict(instruments_rejected),
            'rejection_log_file': self.rejection_log_file
        }


# Global instances (one per strategy)
_honesty_reporters: Dict[str, HonestyReporter] = {}


def get_honesty_reporter(strategy_name: str) -> HonestyReporter:
    """Get or create honesty reporter instance for a strategy"""
    global _honesty_reporters
    if strategy_name not in _honesty_reporters:
        _honesty_reporters[strategy_name] = HonestyReporter(strategy_name)
    return _honesty_reporters[strategy_name]

