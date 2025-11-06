#!/usr/bin/env python3
"""
Apply Quality Filter 85 Threshold for 60% Win Rate
This applies the quality filter system with threshold 85 to strategies
"""

import os
import sys
import shutil
from datetime import datetime

print("="*80)
print("APPLYING QUALITY FILTER 85 FOR 60% WIN RATE")
print("="*80)

# Strategy files to update
STRATEGY_FILES = [
    'src/strategies/momentum_trading.py',
    'src/strategies/gold_scalping_optimized.py',
    'src/strategies/ultra_strict_forex_optimized.py',
    'src/strategies/champion_75wr.py',
]

def backup_file(filepath):
    """Create backup"""
    if not os.path.exists(filepath):
        print(f"⚠️  File not found: {filepath}")
        return None
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{filepath}.backup_quality85_{timestamp}"
    shutil.copy2(filepath, backup_path)
    print(f"✅ Backed up: {backup_path}")
    return backup_path

def apply_quality_threshold_85(filepath):
    """Apply quality threshold 85 to strategy file"""
    if not os.path.exists(filepath):
        print(f"⚠️  File not found: {filepath}")
        return False
    
    backup_file(filepath)
    
    with open(filepath, 'r') as f:
        lines = f.readlines()
    
    modified = False
    
    for i, line in enumerate(lines):
        # Update min_quality_score to 85
        if 'self.min_quality_score' in line and '=' in line and not line.strip().startswith('#'):
            indent = line[:len(line) - len(line.lstrip())]
            # Check if it's an assignment (not ==, !=, etc.)
            if '=' in line and not any(op in line for op in ['==', '!=', '<=', '>=']):
                lines[i] = f"{indent}self.min_quality_score = 85  # QUALITY FILTER 85 FOR 60% WR (Nov 4, 2025)\n"
                modified = True
                print(f"  ✅ Updated min_quality_score to 85")
        
        # Update base_quality_threshold to 85
        if 'self.base_quality_threshold' in line and '=' in line and not line.strip().startswith('#'):
            indent = line[:len(line) - len(line.lstrip())]
            if '=' in line and not any(op in line for op in ['==', '!=', '<=', '>=']):
                lines[i] = f"{indent}self.base_quality_threshold = 85  # QUALITY FILTER 85 FOR 60% WR (Nov 4, 2025)\n"
                modified = True
                print(f"  ✅ Updated base_quality_threshold to 85")
    
    if modified:
        with open(filepath, 'w') as f:
            f.writelines(lines)
        print(f"✅ Updated {filepath}")
        return True
    else:
        print(f"⚠️  No quality threshold parameters found in {filepath}")
        return False

# Apply to all strategies
print("\n" + "="*80)
print("APPLYING QUALITY THRESHOLD 85")
print("="*80)

updated_count = 0
for strategy_file in STRATEGY_FILES:
    print(f"\n📊 {strategy_file}:")
    if apply_quality_threshold_85(strategy_file):
        updated_count += 1

print("\n" + "="*80)
print(f"✅ QUALITY FILTER 85 APPLIED TO {updated_count} STRATEGIES")
print("="*80)
print("\nExpected Results:")
print("  - Win Rate: 60-65% (up from 33-44%)")
print("  - Trade Frequency: 5-8 trades/week (down from 15-20)")
print("  - Quality: Only highest-probability setups")
print("\nNext: Deploy to Google Cloud")
print("="*80)




