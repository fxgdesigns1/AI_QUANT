#!/usr/bin/env python3
"""
Apply October 31, 2025 Monte Carlo Optimization Results
This script applies the optimized parameters to the strategy files
"""

import json
import os
from datetime import datetime
import shutil

# Load optimization results
RESULTS_FILE = "monte_carlo_results_20251031_0003_FINAL.json"

print("="*80)
print("APPLYING OCTOBER 31, 2025 OPTIMIZATION RESULTS")
print("="*80)

# Load results
with open(RESULTS_FILE, 'r') as f:
    results = json.load(f)

print(f"\n✅ Loaded optimization results from {RESULTS_FILE}")

# Optimized parameters per instrument
OPTIMIZED_PARAMS = {
    'GBP_USD': {
        'ema_fast': 3,
        'ema_slow': 12,
        'rsi_oversold': 19.94,
        'rsi_overbought': 80.74,
        'atr_multiplier': 1.43,
        'rr': 2.53
    },
    'XAU_USD': {
        'ema_fast': 3,
        'ema_slow': 29,
        'rsi_oversold': 18.77,
        'rsi_overbought': 79.82,
        'atr_multiplier': 2.88,
        'rr': 3.71
    },
    'EUR_USD': {
        'ema_fast': 8,
        'ema_slow': 37,
        'rsi_oversold': 31.02,
        'rsi_overbought': 76.66,
        'atr_multiplier': 3.84,
        'rr': 4.00
    }
}

# Strategy file mappings
STRATEGY_FILES = {
    'GBP_USD': 'src/strategies/gbp_usd_optimized.py',
    'XAU_USD': 'src/strategies/xau_usd_5m_gold_high_return.py',
    'EUR_USD': 'src/strategies/eur_usd_5m_safe.py'
}

def backup_file(filepath):
    """Create backup of file"""
    if not os.path.exists(filepath):
        print(f"⚠️  File not found: {filepath}")
        return None
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{filepath}.backup_{timestamp}"
    shutil.copy2(filepath, backup_path)
    print(f"✅ Backed up: {backup_path}")
    return backup_path

def apply_params_to_file(filepath, params, instrument):
    """Apply optimized parameters to strategy file"""
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        return False
    
    backup_file(filepath)
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    original_content = content
    
    # Apply parameter replacements
    replacements = {
        'ema_fast': params['ema_fast'],
        'ema_slow': params['ema_slow'],
        'rsi_oversold': params['rsi_oversold'],
        'rsi_overbought': params['rsi_overbought'],
        'atr_multiplier': params['atr_multiplier'],
        'risk_reward_ratio': params['rr']
    }
    
    # Pattern matching for different variable name formats
    patterns = [
        (f"self.ema_fast_period = ", f"self.ema_fast_period = {params['ema_fast']}  # OPTIMIZED Oct 31, 2025"),
        (f"self.ema_slow_period = ", f"self.ema_slow_period = {params['ema_slow']}  # OPTIMIZED Oct 31, 2025"),
        (f"self.ema_fast = ", f"self.ema_fast = {params['ema_fast']}  # OPTIMIZED Oct 31, 2025"),
        (f"self.ema_slow = ", f"self.ema_slow = {params['ema_slow']}  # OPTIMIZED Oct 31, 2025"),
        (f"self.rsi_oversold = ", f"self.rsi_oversold = {params['rsi_oversold']}  # OPTIMIZED Oct 31, 2025"),
        (f"self.rsi_overbought = ", f"self.rsi_overbought = {params['rsi_overbought']}  # OPTIMIZED Oct 31, 2025"),
        (f"self.atr_multiplier = ", f"self.atr_multiplier = {params['atr_multiplier']}  # OPTIMIZED Oct 31, 2025"),
        (f"self.risk_reward_ratio = ", f"self.risk_reward_ratio = {params['rr']}  # OPTIMIZED Oct 31, 2025"),
    ]
    
    lines = content.split('\n')
    modified = False
    
    for i, line in enumerate(lines):
        for pattern, replacement in patterns:
            if pattern in line and '=' in line and not line.strip().startswith('#'):
                # Extract indentation
                indent = line[:len(line) - len(line.lstrip())]
                # Check if this is an assignment line (not ==, !=, etc.)
                if '=' in line and not any(op in line for op in ['==', '!=', '<=', '>=']):
                    lines[i] = f"{indent}{replacement}"
                    modified = True
                    break
    
    if modified:
        with open(filepath, 'w') as f:
            f.write('\n'.join(lines))
        print(f"✅ Updated {filepath}")
        return True
    else:
        print(f"⚠️  No matching patterns found in {filepath}")
        return False

# Apply parameters
print("\n" + "="*80)
print("APPLYING PARAMETERS")
print("="*80)

for instrument, params in OPTIMIZED_PARAMS.items():
    if instrument in STRATEGY_FILES:
        filepath = STRATEGY_FILES[instrument]
        print(f"\n📊 {instrument}:")
        print(f"   EMA Fast: {params['ema_fast']}")
        print(f"   EMA Slow: {params['ema_slow']}")
        print(f"   RSI Oversold: {params['rsi_oversold']}")
        print(f"   RSI Overbought: {params['rsi_overbought']}")
        print(f"   ATR Multiplier: {params['atr_multiplier']}")
        print(f"   Risk/Reward: {params['rr']}")
        
        apply_params_to_file(filepath, params, instrument)
    else:
        print(f"\n⚠️  No strategy file mapped for {instrument}")

print("\n" + "="*80)
print("✅ OPTIMIZATION APPLICATION COMPLETE")
print("="*80)
print("\nNext steps:")
print("1. Review the updated strategy files")
print("2. Test with: python3 -c 'from src.strategies.gbp_usd_optimized import *; print(\"OK\")'")
print("3. Deploy to Google Cloud when ready")
print("\n" + "="*80)


