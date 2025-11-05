#!/usr/bin/env python3
"""
Monitor FTMO Optimizer Progress
Checks if optimizer is running and shows preliminary results if available
"""

import os
import sys
import json
import time
from datetime import datetime

def monitor_optimizer():
    """Monitor the FTMO optimizer progress"""
    print("\n" + "="*70)
    print("🔍 FTMO OPTIMIZER MONITOR")
    print("="*70)
    
    # Check if results file exists
    results_file = 'ftmo_optimization_results.json'
    
    if os.path.exists(results_file):
        print(f"✅ Results file found: {results_file}")
        print(f"   Last modified: {datetime.fromtimestamp(os.path.getmtime(results_file)).strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            with open(results_file, 'r') as f:
                results = json.load(f)
            
            print(f"\n📊 Results Summary:")
            print(f"   Total combinations tested: {len(results)}")
            
            if results:
                # Show top 5
                print(f"\n🏆 Top 5 Results:")
                print(f"{'Rank':<6} {'Win Rate':<12} {'Trades':<10} {'Profit':<12} {'Fitness'}")
                print("-"*70)
                
                for i, r in enumerate(results[:5], 1):
                    print(f"{i:<6} {r['win_rate']:.1f}%{'':<7} {r['trades']:<10} {r['profit_pips']:+.0f}{'':<7} {r['fitness']:.4f}")
                
                # Check for 65%+ win rate
                high_wr = [r for r in results if r['win_rate'] >= 65]
                print(f"\n✅ Combinations with 65%+ win rate: {len(high_wr)}")
                
                if high_wr:
                    best_high_wr = high_wr[0]
                    print(f"\n🎯 Best 65%+ Win Rate Configuration:")
                    print(f"   Win Rate: {best_high_wr['win_rate']:.1f}%")
                    print(f"   Trades: {best_high_wr['trades']}")
                    print(f"   Profit: {best_high_wr['profit_pips']:+.0f} pips")
                    print(f"   Parameters:")
                    for key, value in best_high_wr['params'].items():
                        print(f"      {key}: {value}")
            
        except Exception as e:
            print(f"❌ Error reading results: {e}")
    else:
        print(f"⏳ Results file not yet created")
        print(f"   Optimizer is still running...")
    
    # Check if optimizer process is running
    import subprocess
    try:
        result = subprocess.run(
            ['ps', 'aux'],
            capture_output=True,
            text=True
        )
        
        if 'ftmo_complete_optimizer' in result.stdout:
            print(f"\n✅ Optimizer process is running")
            
            # Extract CPU usage
            for line in result.stdout.split('\n'):
                if 'ftmo_complete_optimizer' in line:
                    parts = line.split()
                    if len(parts) > 2:
                        cpu = parts[2]
                        print(f"   CPU Usage: {cpu}%")
        else:
            print(f"\n⏹️  Optimizer process has finished")
    except Exception as e:
        print(f"❌ Error checking process: {e}")
    
    print("="*70)

if __name__ == "__main__":
    monitor_optimizer()




