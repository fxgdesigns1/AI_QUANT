#!/usr/bin/env python3
"""
Generate final comprehensive optimization report
"""

import json
import os
from datetime import datetime

def generate_report(results_file):
    """Generate comprehensive optimization report"""
    
    with open(results_file, 'r') as f:
        results = json.load(f)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"FINAL_OPTIMIZATION_REPORT_{timestamp}.md"
    
    with open(report_file, 'w') as f:
        f.write("# COMPREHENSIVE STRATEGY OPTIMIZATION REPORT\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S London Time')}\n")
        f.write(f"**Optimization Period:** Past 5 days (Oct 12-17, 2025)\n")
        f.write(f"**Data Source:** OANDA M5 candles\n")
        f.write(f"**Method:** Monte Carlo parameter optimization\n\n")
        
        f.write("="*70 + "\n\n")
        
        # Summary table
        f.write("## QUICK SUMMARY\n\n")
        f.write("| Strategy | Win Rate | Total Trades | P&L | Best Pair |\n")
        f.write("|----------|----------|--------------|-----|----------|\n")
        
        for strategy_name, data in results.items():
            if data.get('top_results'):
                best = data['top_results'][0]
                wr = f"{best['win_rate']:.1f}%"
                trades = best['total_trades']
                pnl = f"{best['total_pnl']:.5f}"
                
                # Find best pair
                best_pair = "N/A"
                if 'trades' in best:
                    pair_stats = {}
                    for trade in best['trades']:
                        pair = trade['pair']
                        if pair not in pair_stats:
                            pair_stats[pair] = {'wins': 0, 'total': 0}
                        pair_stats[pair]['total'] += 1
                        if trade['result'] == 'win':
                            pair_stats[pair]['wins'] += 1
                    
                    best_wr = 0
                    for pair, stats in pair_stats.items():
                        if stats['total'] >= 3:  # At least 3 trades
                            pair_wr = stats['wins'] / stats['total'] * 100
                            if pair_wr > best_wr:
                                best_wr = pair_wr
                                best_pair = f"{pair} ({pair_wr:.0f}%)"
                
                f.write(f"| {strategy_name[:30]} | {wr} | {trades} | {pnl} | {best_pair} |\n")
            else:
                f.write(f"| {strategy_name[:30]} | - | - | - | - |\n")
        
        f.write("\n" + "="*70 + "\n\n")
        
        # Detailed results per strategy
        for strategy_name, data in results.items():
            f.write(f"## {strategy_name}\n\n")
            
            if 'error' in data:
                f.write(f"❌ **Optimization Failed:** {data['error']}\n\n")
                f.write("-"*70 + "\n\n")
                continue
            
            if not data.get('top_results'):
                f.write("⚠️ **No valid results found**\n\n")
                f.write("-"*70 + "\n\n")
                continue
            
            f.write(f"**Instruments:** {', '.join(data['instruments'])}\n")
            f.write(f"**Optimization Time:** {data['optimization_time']:.1f} seconds\n\n")
            
            # Top 3 parameter sets
            for i, result in enumerate(data['top_results'][:3], 1):
                f.write(f"### Rank #{i} Configuration\n\n")
                
                f.write("**Parameters:**\n")
                for param, value in result['params'].items():
                    f.write(f"- `{param}` = {value}\n")
                
                f.write(f"\n**Performance Metrics:**\n")
                f.write(f"- **Total Trades:** {result['total_trades']}\n")
                f.write(f"- **Win Rate:** {result['win_rate']:.1f}%\n")
                f.write(f"- **Wins:** {result['win_count']} | **Losses:** {result['loss_count']}\n")
                f.write(f"- **Total P&L:** {result['total_pnl']:.5f}\n")
                f.write(f"- **Avg Win:** {result['avg_win']:.5f}\n")
                f.write(f"- **Avg Loss:** {result['avg_loss']:.5f}\n")
                f.write(f"- **Combined Score:** {result['score']:.2f}\n\n")
                
                # Pair breakdown
                if 'trades' in result and result['trades']:
                    f.write("**Performance by Pair:**\n\n")
                    pair_stats = {}
                    for trade in result['trades']:
                        pair = trade['pair']
                        if pair not in pair_stats:
                            pair_stats[pair] = {'wins': 0, 'losses': 0, 'pnl': 0}
                        if trade['result'] == 'win':
                            pair_stats[pair]['wins'] += 1
                        else:
                            pair_stats[pair]['losses'] += 1
                        pair_stats[pair]['pnl'] += trade['pnl']
                    
                    for pair in sorted(pair_stats.keys()):
                        stats = pair_stats[pair]
                        total = stats['wins'] + stats['losses']
                        wr = (stats['wins'] / total * 100) if total > 0 else 0
                        f.write(f"- **{pair}**: {total} trades, {wr:.1f}% WR, P&L: {stats['pnl']:.5f}\n")
                    
                    f.write("\n")
                
                if i < 3:
                    f.write("\n---\n\n")
            
            f.write("-"*70 + "\n\n")
        
        # Implementation instructions
        f.write("## IMPLEMENTATION INSTRUCTIONS\n\n")
        f.write("### 1. Review Best Parameters\n")
        f.write("Review the Rank #1 configuration for each strategy above.\n\n")
        f.write("### 2. Apply Parameters\n")
        f.write("Run: `python3 apply_optimized_parameters.py`\n\n")
        f.write("### 3. Test Locally\n")
        f.write("Run: `python3 run_live_scan_now.py`\n\n")
        f.write("### 4. Deploy\n")
        f.write("Run: `gcloud app deploy`\n\n")
        f.write("### 5. Monitor\n")
        f.write("Watch logs and Telegram alerts for 30 minutes.\n\n")
        
        f.write("="*70 + "\n\n")
        f.write(f"**Report Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    print(f"✅ Report generated: {report_file}")
    return report_file


if __name__ == '__main__':
    import glob
    
    # Find latest results file
    result_files = glob.glob("PRIORITY_STRATEGIES_OPTIMIZATION_*.json")
    if result_files:
        latest = sorted(result_files)[-1]
        print(f"Processing: {latest}")
        report = generate_report(latest)
        print(f"\nReport: {report}")
    else:
        print("No results files found!")




