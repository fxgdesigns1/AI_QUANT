#!/usr/bin/env python3
"""
Automatic Learning System Integration Script
Adds learning system to all remaining strategies
"""

import os
import re

# Import block to add
IMPORT_BLOCK = """
# Learning & Honesty System (NEW OCT 21, 2025)
try:
    from ..core.loss_learner import get_loss_learner
    from ..core.early_trend_detector import get_early_trend_detector
    from ..core.honesty_reporter import get_honesty_reporter
    LEARNING_AVAILABLE = True
except ImportError:
    LEARNING_AVAILABLE = False
    logger.warning("⚠️ Learning system not available")
"""

# Initialization block template (customize strategy_name per file)
def get_init_block(strategy_name):
    return f"""
        # ===============================================
        # LEARNING & HONESTY SYSTEM (NEW OCT 21, 2025)
        # ===============================================
        self.learning_enabled = False
        if LEARNING_AVAILABLE:
            try:
                self.loss_learner = get_loss_learner(strategy_name="{strategy_name}")
                self.early_trend = get_early_trend_detector()
                self.honesty = get_honesty_reporter(strategy_name="{strategy_name}")
                self.learning_enabled = True
                logger.info("✅ Loss learning ENABLED - Learns from mistakes")
                logger.info("✅ Early trend detection ENABLED - Catches moves early")
                logger.info("✅ Brutal honesty reporting ENABLED - No sugar-coating")
            except Exception as e:
                logger.warning(f"⚠️ Could not initialize learning system: {{e}}")
                self.loss_learner = None
                self.early_trend = None
                self.honesty = None
        else:
            self.loss_learner = None
            self.early_trend = None
            self.honesty = None
"""

# Methods to add (goes at end of class)
METHODS_BLOCK = """
    def record_trade_result(self, trade_info: Dict, result: str, pnl: float):
        \"\"\"
        Record trade result for learning system (NEW OCT 21, 2025)
        
        Args:
            trade_info: Dict with trade details (instrument, regime, adx, momentum, etc.)
            result: 'WIN' or 'LOSS'
            pnl: Profit/loss amount
        \"\"\"
        if not self.learning_enabled or not self.loss_learner:
            return
        
        if result == 'LOSS':
            self.loss_learner.record_loss(
                instrument=trade_info.get('instrument', 'UNKNOWN'),
                regime=trade_info.get('regime', 'UNKNOWN'),
                adx=trade_info.get('adx', 0.0),
                momentum=trade_info.get('momentum', 0.0),
                volume=trade_info.get('volume', 0.0),
                pnl=pnl,
                conditions=trade_info.get('conditions', {})
            )
            logger.info(f"📉 Recorded loss for learning: {trade_info.get('instrument')} in {trade_info.get('regime')} market")
        else:
            self.loss_learner.record_win(
                instrument=trade_info.get('instrument', 'UNKNOWN'),
                pnl=pnl
            )
            logger.info(f"📈 Recorded win: {trade_info.get('instrument')}")
    
    def get_learning_summary(self) -> Dict:
        \"\"\"Get learning system performance summary\"\"\"
        if not self.learning_enabled or not self.loss_learner:
            return {'enabled': False}
        
        return {
            'enabled': True,
            'performance': self.loss_learner.get_performance_summary(),
            'avoidance_patterns': self.loss_learner.get_avoidance_list()
        }
"""

strategies = [
    ('src/strategies/ultra_strict_forex_optimized.py', 'Ultra Strict Forex - Optimized'),
    ('src/strategies/gold_scalping_optimized.py', 'Gold Scalping - Optimized'),
    ('src/strategies/ultra_strict_v2.py', 'Ultra Strict V2'),
    ('src/strategies/momentum_v2.py', 'Momentum V2'),
    ('src/strategies/champion_75wr.py', '75% WR Champion'),
]

def integrate_strategy(filepath, strategy_name):
    """Integrate learning system into a strategy file"""
    print(f"\nProcessing: {filepath}")
    
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        return False
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Check if already integrated
    if 'loss_learner' in content:
        print(f"✅ Already integrated: {filepath}")
        return True
    
    modified = False
    
    # 1. Add imports after logger setup
    if 'logger = logging.getLogger(__name__)' in content and LEARNING_AVAILABLE not in content:
        content = content.replace(
            'logger = logging.getLogger(__name__)',
            IMPORT_BLOCK + '\nlogger = logging.getLogger(__name__)'
        )
        print("  ✓ Added imports")
        modified = True
    
    # 2. Add initialization in __init__ (find last line before method definitions)
    # Look for common patterns that indicate end of __init__
    patterns = [
        (r'(        logger\.info\(f"✅.*initialized"\))\n\n(    def )', 
         r'\1' + get_init_block(strategy_name) + '\n\n\2'),
        (r'(        self\..*= \[\])\n\n(    def )', 
         r'\1' + get_init_block(strategy_name) + '\n\n\2'),
    ]
    
    for pattern, replacement in patterns:
        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content)
            print("  ✓ Added initialization")
            modified = True
            break
    
    # 3. Add methods before class end (find last method, add before closing)
    # Find the class definition
    class_match = re.search(r'class \w+.*?:', content)
    if class_match:
        # Find where the class ends (look for next class or end of file)
        # Add methods before the last closing of the class
        # Simple heuristic: add before "# Global instance" or similar markers
        markers = ['# Global instance', '# ========', '\n\n# ']
        for marker in markers:
            if marker in content:
                content = content.replace(marker, METHODS_BLOCK + '\n' + marker)
                print("  ✓ Added methods")
                modified = True
                break
    
    if modified:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"✅ Successfully integrated: {filepath}")
        return True
    else:
        print(f"⚠️  Could not fully integrate: {filepath} (manual review needed)")
        return False

def main():
    print("=" * 60)
    print("AUTOMATIC LEARNING SYSTEM INTEGRATION")
    print("=" * 60)
    
    success_count = 0
    for filepath, strategy_name in strategies:
        if integrate_strategy(filepath, strategy_name):
            success_count += 1
    
    print("\n" + "=" * 60)
    print(f"COMPLETED: {success_count}/{len(strategies)} strategies integrated")
    print("=" * 60)
    
    if success_count < len(strategies):
        print("\n⚠️  Some strategies need manual review")
        print("Use the template in STRATEGY_INTEGRATION_TEMPLATE.md")
    else:
        print("\n✅ All strategies successfully integrated!")

if __name__ == '__main__':
    main()

