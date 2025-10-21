#!/usr/bin/env python3
"""
Monitor optimization progress and automatically process results when complete
"""

import os
import sys
import time
import subprocess
from datetime import datetime

def check_if_running():
    """Check if optimization script is still running"""
    result = subprocess.run(
        ["ps", "aux"],
        capture_output=True,
        text=True
    )
    return "optimize_priority_strategies.py" in result.stdout and "grep" not in result.stdout.split("\n")[-2]

def get_latest_progress():
    """Get latest progress from log"""
    try:
        result = subprocess.run(
            ["grep", "Progress:", "priority_opt.log"],
            capture_output=True,
            text=True,
            cwd="/Users/mac/quant_system_clean/google-cloud-trading-system"
        )
        lines = result.stdout.strip().split("\n")
        if lines and lines[-1]:
            return lines[-1].strip()
    except:
        pass
    return "No progress info"

def check_for_results():
    """Check if results files have been generated"""
    import glob
    result_files = glob.glob("/Users/mac/quant_system_clean/google-cloud-trading-system/PRIORITY_STRATEGIES_OPTIMIZATION_*.json")
    if result_files:
        return sorted(result_files)[-1]
    return None

def main():
    print("\n" + "="*70)
    print("OPTIMIZATION MONITOR")
    print("="*70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70 + "\n")
    
    last_progress = ""
    check_count = 0
    
    while True:
        is_running = check_if_running()
        current_progress = get_latest_progress()
        
        if current_progress != last_progress:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {current_progress}")
            last_progress = current_progress
        
        if not is_running:
            print("\n" + "="*70)
            print("✅ OPTIMIZATION PROCESS COMPLETED!")
            print("="*70 + "\n")
            
            # Check for results
            results_file = check_for_results()
            if results_file:
                print(f"📊 Results file: {results_file}")
                print("\nProcessing results...")
                
                # Here you could automatically call apply_optimized_parameters.py
                # or send Telegram notification
                
            else:
                print("⚠️ No results file found - optimization may have failed")
            
            break
        
        check_count += 1
        if check_count % 12 == 0:  # Every minute
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Still running... ({current_progress})")
        
        time.sleep(5)  # Check every 5 seconds

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Monitoring stopped by user")
        print("Optimization process is still running in background (PID in priority_opt.log)")




