#!/usr/bin/env python3
"""
Live Trading Learnings to Backtesting System Updater
Analyzes recent live market performance and sends improvements to backtesting
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import os

logger = logging.getLogger(__name__)


@dataclass
class BacktestingUpdate:
    """Update to be sent to backtesting system"""
    strategy_name: str
    instrument: str
    parameter_name: str
    old_value: Any
    new_value: Any
    reason: str
    confidence: float  # 0.0-1.0
    data_points: int
    improvement_expected: str


@dataclass
class LiveMarketLearning:
    """Learning from live market data"""
    learning_type: str  # 'slippage', 'spread', 'volatility', 'win_rate', 'session_performance'
    instrument: str
    session: Optional[str]
    data: Dict[str, Any]
    recommendation: str
    timestamp: str


class LiveLearningsToBacktestUpdater:
    """
    Analyzes live trading performance from past few weeks
    Generates backtesting parameter updates
    """
    
    def __init__(self, export_path: str = None):
        self.name = "LiveLearningsUpdater"
        
        # Export location
        if export_path is None:
            export_path = "/Users/mac/quant_system_clean/google-cloud-trading-system/backtesting_updates"
        
        self.export_path = export_path
        os.makedirs(export_path, exist_ok=True)
        
        # Learnings storage
        self.learnings: List[LiveMarketLearning] = []
        self.updates: List[BacktestingUpdate] = []
        
        logger.info(f"✅ {self.name} initialized")
        logger.info(f"   Export path: {export_path}")
    
    def analyze_live_performance_vs_backtest(self, 
                                            optimization_results_path: str = None) -> Dict[str, Any]:
        """
        Analyze how live performance compares to backtested expectations
        
        Returns learnings and recommended updates
        """
        
        if optimization_results_path is None:
            optimization_results_path = "/Users/mac/quant_system_clean/google-cloud-trading-system/optimization_results.json"
        
        try:
            with open(optimization_results_path, 'r') as f:
                backtest_results = json.load(f)
        except Exception as e:
            logger.error(f"❌ Failed to load backtest results: {e}")
            return {}
        
        analysis = {
            'timestamp': datetime.now().isoformat(),
            'learnings': [],
            'recommended_updates': [],
            'summary': {}
        }
        
        # Analyze each strategy
        for strategy_name, strategy_data in backtest_results.items():
            logger.info(f"📊 Analyzing {strategy_name}...")
            
            strategy_learnings = self._analyze_strategy_performance(
                strategy_name, 
                strategy_data
            )
            
            analysis['learnings'].extend(strategy_learnings)
        
        # Generate recommended updates based on learnings
        analysis['recommended_updates'] = self._generate_recommended_updates(
            analysis['learnings']
        )
        
        # Summary
        analysis['summary'] = {
            'total_learnings': len(analysis['learnings']),
            'total_updates': len(analysis['recommended_updates']),
            'high_confidence_updates': sum(1 for u in analysis['recommended_updates'] 
                                          if u.get('confidence', 0) >= 0.8),
            'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return analysis
    
    def _analyze_strategy_performance(self, 
                                     strategy_name: str, 
                                     strategy_data: Dict) -> List[Dict]:
        """Analyze individual strategy performance"""
        
        learnings = []
        
        for instrument, params in strategy_data.items():
            # Learning #1: Are we getting enough trades?
            if 'trades' in params:
                trades = params['trades']
                
                if trades < 5:
                    learnings.append({
                        'type': 'insufficient_trades',
                        'strategy': strategy_name,
                        'instrument': instrument,
                        'data': {'trades': trades},
                        'recommendation': f'Thresholds too strict - only {trades} trades. Consider loosening entry criteria.',
                        'confidence': 0.9,
                        'timestamp': datetime.now().isoformat()
                    })
                elif trades > 100:
                    learnings.append({
                        'type': 'excessive_trades',
                        'strategy': strategy_name,
                        'instrument': instrument,
                        'data': {'trades': trades},
                        'recommendation': f'Too many trades ({trades}) - may be overtrading. Consider tightening entry criteria.',
                        'confidence': 0.7,
                        'timestamp': datetime.now().isoformat()
                    })
            
            # Learning #2: Win rate analysis
            if 'wins' in params and 'losses' in params and 'trades' in params:
                wins = params['wins']
                losses = params['losses']
                total = params['trades']
                
                if total > 0:
                    win_rate = wins / total if total > 0 else 0
                    
                    if win_rate < 0.4:
                        learnings.append({
                            'type': 'low_win_rate',
                            'strategy': strategy_name,
                            'instrument': instrument,
                            'data': {'win_rate': win_rate, 'wins': wins, 'losses': losses},
                            'recommendation': f'Win rate {win_rate:.1%} is too low. Strategy needs optimization or should be disabled for {instrument}.',
                            'confidence': 0.95,
                            'timestamp': datetime.now().isoformat()
                        })
                    elif win_rate > 0.8 and total > 20:
                        learnings.append({
                            'type': 'excellent_win_rate',
                            'strategy': strategy_name,
                            'instrument': instrument,
                            'data': {'win_rate': win_rate, 'wins': wins, 'losses': losses},
                            'recommendation': f'Win rate {win_rate:.1%} is excellent! Can potentially increase position size or loosen criteria for more trades.',
                            'confidence': 0.8,
                            'timestamp': datetime.now().isoformat()
                        })
            
            # Learning #3: P&L analysis
            if 'pnl' in params:
                pnl = params['pnl']
                
                if pnl < -0.001:  # Losing more than 0.1%
                    learnings.append({
                        'type': 'negative_pnl',
                        'strategy': strategy_name,
                        'instrument': instrument,
                        'data': {'pnl': pnl, 'pnl_pct': pnl * 100},
                        'recommendation': f'Negative P&L ({pnl:.4f}). Consider disabling {instrument} for this strategy or adjusting parameters.',
                        'confidence': 0.9,
                        'timestamp': datetime.now().isoformat()
                    })
        
        return learnings
    
    def _generate_recommended_updates(self, learnings: List[Dict]) -> List[Dict]:
        """Generate specific parameter updates based on learnings"""
        
        updates = []
        
        for learning in learnings:
            learning_type = learning.get('type')
            strategy = learning.get('strategy')
            instrument = learning.get('instrument')
            data = learning.get('data', {})
            
            # Update #1: Adjust signal strength for low-performing instruments
            if learning_type == 'low_win_rate':
                if strategy == 'UltraStrictForex':
                    current_threshold = data.get('min_signal_strength', 0.35)
                    new_threshold = min(0.5, current_threshold + 0.05)
                    
                    updates.append({
                        'strategy': strategy,
                        'instrument': instrument,
                        'parameter': 'min_signal_strength',
                        'old_value': current_threshold,
                        'new_value': new_threshold,
                        'reason': f'Win rate {data.get("win_rate", 0):.1%} too low - increasing threshold',
                        'confidence': 0.8,
                        'data_points': data.get('trades', 0),
                        'action': 'TIGHTEN_ENTRY'
                    })
            
            # Update #2: Loosen criteria for excellent performers
            elif learning_type == 'excellent_win_rate':
                if strategy == 'UltraStrictForex':
                    current_threshold = data.get('min_signal_strength', 0.35)
                    new_threshold = max(0.30, current_threshold - 0.05)
                    
                    updates.append({
                        'strategy': strategy,
                        'instrument': instrument,
                        'parameter': 'min_signal_strength',
                        'old_value': current_threshold,
                        'new_value': new_threshold,
                        'reason': f'Win rate {data.get("win_rate", 0):.1%} excellent - can take more trades',
                        'confidence': 0.7,
                        'data_points': data.get('trades', 0),
                        'action': 'LOOSEN_ENTRY'
                    })
            
            # Update #3: Adjust momentum thresholds
            elif learning_type == 'insufficient_trades':
                if strategy == 'Momentum':
                    # Current min_momentum is likely too high
                    current_momentum = data.get('min_momentum', 0.002)
                    new_momentum = max(0.001, current_momentum - 0.0005)
                    
                    updates.append({
                        'strategy': strategy,
                        'instrument': instrument,
                        'parameter': 'min_momentum',
                        'old_value': current_momentum,
                        'new_value': new_momentum,
                        'reason': f'Only {data.get("trades", 0)} trades - momentum threshold too high',
                        'confidence': 0.75,
                        'data_points': data.get('trades', 0),
                        'action': 'LOOSEN_ENTRY'
                    })
            
            # Update #4: Disable losing instruments
            elif learning_type == 'negative_pnl':
                if data.get('pnl', 0) < -0.005:  # Lost more than 0.5%
                    updates.append({
                        'strategy': strategy,
                        'instrument': instrument,
                        'parameter': 'enabled',
                        'old_value': True,
                        'new_value': False,
                        'reason': f'Negative P&L {data.get("pnl", 0):.4f} - disable this pair',
                        'confidence': 0.85,
                        'data_points': data.get('trades', 0),
                        'action': 'DISABLE_INSTRUMENT'
                    })
        
        return updates
    
    def export_updates_to_backtesting_system(self, 
                                            analysis: Dict = None) -> str:
        """
        Export all learnings and updates to backtesting system
        
        Returns path to exported file
        """
        
        if analysis is None:
            analysis = self.analyze_live_performance_vs_backtest()
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Export full analysis
        analysis_file = os.path.join(
            self.export_path,
            f"backtesting_updates_{timestamp}.json"
        )
        
        with open(analysis_file, 'w') as f:
            json.dump(analysis, f, indent=2)
        
        logger.info(f"✅ Backtesting updates exported: {analysis_file}")
        
        # Export human-readable summary
        summary_file = os.path.join(
            self.export_path,
            f"BACKTESTING_UPDATES_SUMMARY_{timestamp}.md"
        )
        
        self._create_summary_report(analysis, summary_file)
        
        # Export updated optimization_results.json
        if analysis['recommended_updates']:
            self._export_updated_optimization_params(analysis, timestamp)
        
        return analysis_file
    
    def _export_updated_optimization_params(self, 
                                           analysis: Dict, 
                                           timestamp: str):
        """Export new optimization_results.json with recommended updates"""
        
        # Load current optimization results
        try:
            with open('/Users/mac/quant_system_clean/google-cloud-trading-system/optimization_results.json', 'r') as f:
                current_params = json.load(f)
        except:
            current_params = {}
        
        # Apply high-confidence updates
        updated_params = current_params.copy()
        updates_applied = []
        
        for update in analysis['recommended_updates']:
            if update.get('confidence', 0) >= 0.75:  # Only high confidence
                strategy = update['strategy']
                instrument = update['instrument']
                parameter = update['parameter']
                new_value = update['new_value']
                
                if strategy in updated_params and instrument in updated_params[strategy]:
                    updated_params[strategy][instrument][parameter] = new_value
                    updates_applied.append(update)
                    logger.info(f"✅ Applied update: {strategy}/{instrument}/{parameter} = {new_value}")
        
        # Export new file
        if updates_applied:
            new_file = os.path.join(
                self.export_path,
                f"optimization_results_UPDATED_{timestamp}.json"
            )
            
            with open(new_file, 'w') as f:
                json.dump(updated_params, f, indent=2)
            
            logger.info(f"✅ Updated optimization params: {new_file}")
            logger.info(f"   Applied {len(updates_applied)} high-confidence updates")
            
            # Create instructions file
            instructions = f"""# BACKTESTING SYSTEM UPDATE INSTRUCTIONS

## Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Updates Applied: {len(updates_applied)}

### To Apply These Updates:

1. **Backup your current optimization_results.json:**
   ```bash
   cp optimization_results.json optimization_results_BACKUP_{timestamp}.json
   ```

2. **Replace with new version:**
   ```bash
   cp {new_file} optimization_results.json
   ```

3. **Restart your backtesting system** to load new parameters

4. **Verify results** after 24 hours of live trading

## Changes Made:

"""
            
            for update in updates_applied:
                instructions += f"\n### {update['strategy']} - {update['instrument']}\n"
                instructions += f"- **Parameter:** `{update['parameter']}`\n"
                instructions += f"- **Old Value:** `{update['old_value']}`\n"
                instructions += f"- **New Value:** `{update['new_value']}`\n"
                instructions += f"- **Reason:** {update['reason']}\n"
                instructions += f"- **Confidence:** {update['confidence']:.1%}\n"
                instructions += f"- **Action:** {update['action']}\n\n"
            
            instructions_file = os.path.join(
                self.export_path,
                f"UPDATE_INSTRUCTIONS_{timestamp}.md"
            )
            
            with open(instructions_file, 'w') as f:
                f.write(instructions)
            
            logger.info(f"✅ Instructions created: {instructions_file}")
    
    def _create_summary_report(self, analysis: Dict, output_file: str):
        """Create human-readable summary report"""
        
        with open(output_file, 'w') as f:
            f.write("# LIVE TRADING LEARNINGS → BACKTESTING UPDATES\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("---\n\n")
            
            # Summary
            summary = analysis.get('summary', {})
            f.write("## 📊 SUMMARY\n\n")
            f.write(f"- **Total Learnings Identified:** {summary.get('total_learnings', 0)}\n")
            f.write(f"- **Recommended Updates:** {summary.get('total_updates', 0)}\n")
            f.write(f"- **High Confidence Updates:** {summary.get('high_confidence_updates', 0)}\n")
            f.write(f"- **Analysis Date:** {summary.get('analysis_date', 'N/A')}\n\n")
            
            # Key Learnings
            learnings = analysis.get('learnings', [])
            if learnings:
                f.write("## 🔍 KEY LEARNINGS FROM LIVE TRADING\n\n")
                
                for i, learning in enumerate(learnings[:10], 1):  # Top 10
                    f.write(f"### {i}. {learning.get('type', 'unknown').replace('_', ' ').title()}\n\n")
                    f.write(f"- **Strategy:** {learning.get('strategy', 'N/A')}\n")
                    f.write(f"- **Instrument:** {learning.get('instrument', 'N/A')}\n")
                    f.write(f"- **Data:** {json.dumps(learning.get('data', {}), indent=2)}\n")
                    f.write(f"- **Recommendation:** {learning.get('recommendation', 'N/A')}\n")
                    f.write(f"- **Confidence:** {learning.get('confidence', 0):.1%}\n\n")
            
            # Recommended Updates
            updates = analysis.get('recommended_updates', [])
            if updates:
                f.write("## 🔧 RECOMMENDED BACKTESTING UPDATES\n\n")
                
                high_conf = [u for u in updates if u.get('confidence', 0) >= 0.8]
                medium_conf = [u for u in updates if 0.6 <= u.get('confidence', 0) < 0.8]
                
                if high_conf:
                    f.write("### 🔴 HIGH CONFIDENCE (Apply Immediately)\n\n")
                    for update in high_conf:
                        f.write(f"#### {update.get('strategy')} - {update.get('instrument')}\n\n")
                        f.write(f"- **Parameter:** `{update.get('parameter')}`\n")
                        f.write(f"- **Change:** `{update.get('old_value')}` → `{update.get('new_value')}`\n")
                        f.write(f"- **Reason:** {update.get('reason')}\n")
                        f.write(f"- **Confidence:** {update.get('confidence', 0):.1%}\n")
                        f.write(f"- **Based on:** {update.get('data_points', 0)} data points\n\n")
                
                if medium_conf:
                    f.write("### 🟡 MEDIUM CONFIDENCE (Consider Testing)\n\n")
                    for update in medium_conf:
                        f.write(f"#### {update.get('strategy')} - {update.get('instrument')}\n\n")
                        f.write(f"- **Parameter:** `{update.get('parameter')}`\n")
                        f.write(f"- **Change:** `{update.get('old_value')}` → `{update.get('new_value')}`\n")
                        f.write(f"- **Reason:** {update.get('reason')}\n\n")
            
            f.write("\n---\n\n")
            f.write("**Next Steps:**\n")
            f.write("1. Review high confidence updates\n")
            f.write("2. Apply updates to backtesting system\n")
            f.write("3. Run new backtests to validate improvements\n")
            f.write("4. Monitor live trading performance for 1 week\n")
            f.write("5. Iterate based on results\n")
        
        logger.info(f"✅ Summary report created: {output_file}")


# Global instance
_updater = None

def get_learnings_updater() -> LiveLearningsToBacktestUpdater:
    """Get global updater instance"""
    global _updater
    if _updater is None:
        _updater = LiveLearningsToBacktestUpdater()
    return _updater


# CLI interface
if __name__ == "__main__":
    print("=" * 60)
    print("LIVE TRADING LEARNINGS → BACKTESTING UPDATER")
    print("=" * 60)
    print()
    
    # Create updater
    updater = LiveLearningsToBacktestUpdater()
    
    # Analyze performance
    print("📊 Analyzing live trading performance vs backtested expectations...")
    analysis = updater.analyze_live_performance_vs_backtest()
    
    # Show summary
    print(f"\n✅ Analysis Complete!")
    print(f"   - Learnings identified: {analysis['summary']['total_learnings']}")
    print(f"   - Recommended updates: {analysis['summary']['total_updates']}")
    print(f"   - High confidence: {analysis['summary']['high_confidence_updates']}")
    
    # Export
    print(f"\n📤 Exporting updates to backtesting system...")
    export_file = updater.export_updates_to_backtesting_system(analysis)
    
    print(f"\n✅ Export Complete!")
    print(f"   - Updates file: {export_file}")
    print(f"   - Check: {updater.export_path}/")
    print()
    print("=" * 60)
    print("REVIEW THE UPDATES AND APPLY TO YOUR BACKTESTING SYSTEM")
    print("=" * 60)























