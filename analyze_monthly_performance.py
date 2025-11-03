#!/usr/bin/env python3
"""
Comprehensive Monthly & Weekly Performance Analysis
Analyzes October 2025 performance by strategy and pair
Creates monthly breakdown, monthly roadmap, weekly breakdown, and weekly roadmap
"""

import os
import sys
import sqlite3
import json
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Any, Optional
import yaml

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'google-cloud-trading-system', 'src'))

def load_accounts_config():
    """Load accounts configuration"""
    accounts_file = os.path.join(os.path.dirname(__file__), 'google-cloud-trading-system', 'accounts.yaml')
    if os.path.exists(accounts_file):
        with open(accounts_file, 'r') as f:
            return yaml.safe_load(f)
    return None

def get_database_path():
    """Find the trading database"""
    possible_paths = [
        'google-cloud-trading-system/data/trading.db',
        'google-cloud-trading-system/analytics/data/trading.db',
        'data/trading.db',
        '/tmp/trading.db'
    ]
    
    for path in possible_paths:
        full_path = os.path.join(os.path.dirname(__file__), path)
        if os.path.exists(full_path):
            return full_path
    
    # Return default path (will create if needed)
    return os.path.join(os.path.dirname(__file__), 'google-cloud-trading-system', 'data', 'trading.db')

def query_trades(db_path: str, start_date: datetime, end_date: datetime, 
                 account_id: Optional[str] = None, strategy: Optional[str] = None) -> List[Dict]:
    """Query trades from database"""
    if not os.path.exists(db_path):
        return []
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Try to get table schema first
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        if 'trades' not in tables:
            conn.close()
            return []
        
        # Build query
        query = "SELECT * FROM trades WHERE 1=1"
        params = []
        
        if start_date:
            query += " AND entry_time >= ?"
            params.append(start_date.isoformat())
        
        if end_date:
            query += " AND entry_time <= ?"
            params.append(end_date.isoformat())
        
        if account_id:
            query += " AND account_id = ?"
            params.append(account_id)
        
        if strategy:
            query += " AND strategy_name = ?"
            params.append(strategy)
        
        query += " ORDER BY entry_time ASC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        trades = []
        for row in rows:
            trade = dict(row)
            trades.append(trade)
        
        conn.close()
        return trades
    
    except Exception as e:
        print(f"⚠️  Database query error: {e}")
        return []

def analyze_trades(trades: List[Dict]) -> Dict[str, Any]:
    """Analyze trade data"""
    if not trades:
        return {
            'total_trades': 0,
            'closed_trades': 0,
            'open_trades': 0,
            'total_pnl': 0.0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'profit_factor': 0.0,
            'max_drawdown': 0.0,
            'by_strategy': {},
            'by_pair': {},
            'by_day': {}
        }
    
    analysis = {
        'total_trades': len(trades),
        'closed_trades': 0,
        'open_trades': 0,
        'total_pnl': 0.0,
        'winning_trades': 0,
        'losing_trades': 0,
        'win_rate': 0.0,
        'avg_win': 0.0,
        'avg_loss': 0.0,
        'profit_factor': 0.0,
        'max_drawdown': 0.0,
        'by_strategy': defaultdict(lambda: {
            'trades': 0,
            'closed': 0,
            'pnl': 0.0,
            'wins': 0,
            'losses': 0,
            'win_rate': 0.0
        }),
        'by_pair': defaultdict(lambda: {
            'trades': 0,
            'closed': 0,
            'pnl': 0.0,
            'wins': 0,
            'losses': 0,
            'win_rate': 0.0
        }),
        'by_day': defaultdict(lambda: {
            'trades': 0,
            'closed': 0,
            'pnl': 0.0
        })
    }
    
    total_wins = 0.0
    total_losses = 0.0
    winning_amount = 0.0
    losing_amount = 0.0
    
    for trade in trades:
        status = trade.get('status', 'open')
        pnl = trade.get('realized_pl', trade.get('net_pl', trade.get('profit_loss', 0.0)))
        
        strategy = trade.get('strategy_name', trade.get('strategy', 'unknown'))
        instrument = trade.get('instrument', 'unknown')
        entry_time = trade.get('entry_time', trade.get('timestamp', ''))
        
        if entry_time:
            try:
                if isinstance(entry_time, str):
                    entry_date = datetime.fromisoformat(entry_time.split('.')[0])
                else:
                    entry_date = entry_time
                day_key = entry_date.strftime('%Y-%m-%d')
            except:
                day_key = 'unknown'
        else:
            day_key = 'unknown'
        
        analysis['by_strategy'][strategy]['trades'] += 1
        analysis['by_pair'][instrument]['trades'] += 1
        analysis['by_day'][day_key]['trades'] += 1
        
        if status == 'closed' and pnl is not None:
            analysis['closed_trades'] += 1
            analysis['total_pnl'] += float(pnl)
            
            analysis['by_strategy'][strategy]['closed'] += 1
            analysis['by_strategy'][strategy]['pnl'] += float(pnl)
            analysis['by_pair'][instrument]['closed'] += 1
            analysis['by_pair'][instrument]['pnl'] += float(pnl)
            analysis['by_day'][day_key]['closed'] += 1
            analysis['by_day'][day_key]['pnl'] += float(pnl)
            
            if float(pnl) > 0:
                analysis['winning_trades'] += 1
                analysis['by_strategy'][strategy]['wins'] += 1
                analysis['by_pair'][instrument]['wins'] += 1
                winning_amount += float(pnl)
            else:
                analysis['losing_trades'] += 1
                analysis['by_strategy'][strategy]['losses'] += 1
                analysis['by_pair'][instrument]['losses'] += 1
                losing_amount += abs(float(pnl))
        else:
            analysis['open_trades'] += 1
    
    # Calculate metrics
    if analysis['closed_trades'] > 0:
        analysis['win_rate'] = (analysis['winning_trades'] / analysis['closed_trades']) * 100
    
    if analysis['winning_trades'] > 0:
        analysis['avg_win'] = winning_amount / analysis['winning_trades']
    
    if analysis['losing_trades'] > 0:
        analysis['avg_loss'] = losing_amount / analysis['losing_trades']
    
    if losing_amount > 0:
        analysis['profit_factor'] = winning_amount / losing_amount
    
    # Calculate win rates by strategy and pair
    for strategy, data in analysis['by_strategy'].items():
        if data['closed'] > 0:
            data['win_rate'] = (data['wins'] / data['closed']) * 100
    
    for pair, data in analysis['by_pair'].items():
        if data['closed'] > 0:
            data['win_rate'] = (data['wins'] / data['closed']) * 100
    
    return analysis

def generate_monthly_report(october_data: Dict, accounts_config: Dict) -> str:
    """Generate comprehensive monthly report"""
    report = []
    report.append("# 📊 OCTOBER 2025 MONTHLY PERFORMANCE ANALYSIS")
    report.append(f"**Generated:** {datetime.now().strftime('%B %d, %Y - %H:%M:%S')}")
    report.append("")
    report.append("---")
    report.append("")
    
    # Overall Summary
    report.append("## 📈 OVERALL OCTOBER PERFORMANCE")
    report.append("")
    report.append(f"- **Total Trades:** {october_data['total_trades']}")
    report.append(f"- **Closed Trades:** {october_data['closed_trades']}")
    report.append(f"- **Open Trades:** {october_data['open_trades']}")
    report.append(f"- **Total P&L:** ${october_data['total_pnl']:,.2f}")
    report.append(f"- **Win Rate:** {october_data['win_rate']:.1f}%")
    report.append(f"- **Profit Factor:** {october_data['profit_factor']:.2f}")
    report.append(f"- **Average Win:** ${october_data['avg_win']:,.2f}")
    report.append(f"- **Average Loss:** ${october_data['avg_loss']:,.2f}")
    report.append("")
    report.append("---")
    report.append("")
    
    # Performance by Strategy
    report.append("## 🎯 PERFORMANCE BY STRATEGY")
    report.append("")
    if october_data['by_strategy']:
        report.append("| Strategy | Trades | Closed | P&L | Win Rate | Wins | Losses |")
        report.append("|----------|--------|--------|-----|----------|------|--------|")
        for strategy, data in sorted(october_data['by_strategy'].items(), 
                                     key=lambda x: x[1]['pnl'], reverse=True):
            pnl_str = f"${data['pnl']:,.2f}" if data['pnl'] != 0 else "$0.00"
            win_rate_str = f"{data['win_rate']:.1f}%" if data['closed'] > 0 else "N/A"
            report.append(f"| {strategy} | {data['trades']} | {data['closed']} | {pnl_str} | {win_rate_str} | {data['wins']} | {data['losses']} |")
    else:
        report.append("⚠️  No strategy data available")
    report.append("")
    report.append("---")
    report.append("")
    
    # Performance by Pair
    report.append("## 💱 PERFORMANCE BY TRADING PAIR")
    report.append("")
    if october_data['by_pair']:
        report.append("| Pair | Trades | Closed | P&L | Win Rate | Wins | Losses |")
        report.append("|------|--------|--------|-----|----------|------|--------|")
        for pair, data in sorted(october_data['by_pair'].items(), 
                                 key=lambda x: x[1]['pnl'], reverse=True):
            pnl_str = f"${data['pnl']:,.2f}" if data['pnl'] != 0 else "$0.00"
            win_rate_str = f"{data['win_rate']:.1f}%" if data['closed'] > 0 else "N/A"
            report.append(f"| {pair} | {data['trades']} | {data['closed']} | {pnl_str} | {win_rate_str} | {data['wins']} | {data['losses']} |")
    else:
        report.append("⚠️  No pair data available")
    report.append("")
    report.append("---")
    report.append("")
    
    # Daily Performance
    report.append("## 📅 DAILY PERFORMANCE BREAKDOWN")
    report.append("")
    if october_data['by_day']:
        report.append("| Date | Trades | Closed | P&L |")
        report.append("|------|--------|--------|-----|")
        for day in sorted(october_data['by_day'].keys()):
            data = october_data['by_day'][day]
            pnl_str = f"${data['pnl']:,.2f}" if data['pnl'] != 0 else "$0.00"
            report.append(f"| {day} | {data['trades']} | {data['closed']} | {pnl_str} |")
    else:
        report.append("⚠️  No daily data available")
    report.append("")
    
    return "\n".join(report)

def generate_monthly_roadmap(october_data: Dict, accounts_config: Dict) -> str:
    """Generate November monthly roadmap"""
    report = []
    report.append("# 🗺️ NOVEMBER 2025 MONTHLY ROADMAP")
    report.append(f"**Generated:** {datetime.now().strftime('%B %d, %Y - %H:%M:%S')}")
    report.append(f"**Period:** November 1-30, 2025")
    report.append("")
    report.append("---")
    report.append("")
    
    # Based on October performance
    report.append("## 🎯 MONTHLY OBJECTIVES")
    report.append("")
    
    if october_data['total_trades'] > 0:
        # Calculate targets based on October
        avg_daily_trades = october_data['total_trades'] / 30
        target_monthly_trades = int(avg_daily_trades * 30 * 1.1)  # 10% growth
        target_pnl = abs(october_data['total_pnl']) * 1.2  # 20% growth if positive, else recovery
        
        report.append(f"- **Target Trades:** {target_monthly_trades} trades")
        report.append(f"- **Target P&L:** ${target_pnl:,.2f}")
        report.append(f"- **Target Win Rate:** {max(october_data['win_rate'], 60):.1f}%+")
    else:
        report.append("- **Target Trades:** Establish baseline performance")
        report.append("- **Target P&L:** Focus on consistency over profits")
        report.append("- **Target Win Rate:** 60%+ minimum")
    
    report.append("")
    report.append("---")
    report.append("")
    
    # Strategy Roadmap
    report.append("## 🤖 STRATEGY ROADMAP BY ACCOUNT")
    report.append("")
    
    if accounts_config and 'accounts' in accounts_config:
        for account in accounts_config['accounts']:
            if not account.get('active', False):
                continue
            
            account_id = account['id']
            strategy = account['strategy']
            name = account['name']
            instruments = account.get('instruments', account.get('trading_pairs', []))
            
            strategy_data = october_data['by_strategy'].get(strategy, {})
            
            report.append(f"### **{name}** (Account: {account_id[-3:]})")
            report.append("")
            report.append(f"**Strategy:** {strategy}")
            report.append(f"**Instruments:** {', '.join(instruments)}")
            report.append("")
            
            if strategy_data and strategy_data['trades'] > 0:
                pnl = strategy_data['pnl']
                win_rate = strategy_data['win_rate']
                
                report.append(f"**October Performance:**")
                report.append(f"- Trades: {strategy_data['trades']}")
                report.append(f"- P&L: ${pnl:,.2f}")
                report.append(f"- Win Rate: {win_rate:.1f}%")
                report.append("")
                
                if pnl > 0 and win_rate > 60:
                    report.append("✅ **November Plan:** Scale up successful strategy")
                    report.append("- Increase position size by 10-20%")
                    report.append("- Maintain current risk parameters")
                elif win_rate > 60 and pnl < 0:
                    report.append("⚠️ **November Plan:** Adjust risk management")
                    report.append("- Reduce average loss size")
                    report.append("- Tighten stop-losses")
                else:
                    report.append("🔧 **November Plan:** Optimize strategy")
                    report.append("- Review entry criteria")
                    report.append("- Test parameter adjustments")
            else:
                report.append("📊 **November Plan:** Establish baseline")
                report.append("- Monitor first week performance")
                report.append("- Adjust based on initial results")
            
            report.append("")
    else:
        report.append("⚠️  Account configuration not available")
    
    report.append("---")
    report.append("")
    
    # Pair-Specific Roadmap
    report.append("## 💱 TRADING PAIR ROADMAP")
    report.append("")
    
    if october_data['by_pair']:
        for pair, data in sorted(october_data['by_pair'].items(), 
                                key=lambda x: x[1]['pnl'], reverse=True):
            report.append(f"### **{pair}**")
            report.append("")
            report.append(f"**October:** {data['trades']} trades, ${data['pnl']:,.2f} P&L, {data['win_rate']:.1f}% WR")
            report.append("")
            
            if data['pnl'] > 0 and data['win_rate'] > 60:
                report.append("✅ **November Focus:** Continue trading")
                report.append(f"- Target: {int(data['trades'] * 1.1)} trades")
                report.append(f"- Maintain {data['win_rate']:.1f}% win rate")
            elif data['win_rate'] > 55:
                report.append("⚠️ **November Focus:** Improve risk/reward")
                report.append("- Review stop-loss placement")
                report.append("- Optimize take-profit levels")
            else:
                report.append("🔧 **November Focus:** Strategy review")
                report.append("- Analyze losing trades")
                report.append("- Test alternative approaches")
            report.append("")
    else:
        report.append("📊 **All Pairs:** Focus on building trade history")
    
    report.append("---")
    report.append("")
    
    # Key Milestones
    report.append("## 🏆 KEY MILESTONES")
    report.append("")
    report.append("### Week 1 (Nov 1-7):")
    report.append("- Establish November baseline")
    report.append("- Review and adjust from October learnings")
    report.append("- Target: Consistent daily trading")
    report.append("")
    report.append("### Week 2 (Nov 8-14):")
    report.append("- Optimize top performers")
    report.append("- Refine underperformers")
    report.append("- Target: 20% improvement in win rate")
    report.append("")
    report.append("### Week 3 (Nov 15-21):")
    report.append("- Scale successful strategies")
    report.append("- Focus on risk management")
    report.append("- Target: Consistent profitability")
    report.append("")
    report.append("### Week 4 (Nov 22-30):")
    report.append("- Review full month performance")
    report.append("- Plan December optimizations")
    report.append("- Target: Monthly goals achievement")
    
    return "\n".join(report)

def generate_weekly_report(week_data: Dict, accounts_config: Dict) -> str:
    """Generate current week breakdown"""
    report = []
    
    # Determine current week
    today = datetime.now()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    
    report.append("# 📅 WEEKLY PERFORMANCE BREAKDOWN")
    report.append(f"**Week:** {week_start.strftime('%B %d')} - {week_end.strftime('%B %d, %Y')}")
    report.append(f"**Generated:** {datetime.now().strftime('%B %d, %Y - %H:%M:%S')}")
    report.append("")
    report.append("---")
    report.append("")
    
    # Week Summary
    report.append("## 📊 WEEK-TO-DATE PERFORMANCE")
    report.append("")
    report.append(f"- **Total Trades:** {week_data['total_trades']}")
    report.append(f"- **Closed Trades:** {week_data['closed_trades']}")
    report.append(f"- **Open Trades:** {week_data['open_trades']}")
    report.append(f"- **Total P&L:** ${week_data['total_pnl']:,.2f}")
    report.append(f"- **Win Rate:** {week_data['win_rate']:.1f}%")
    report.append(f"- **Profit Factor:** {week_data['profit_factor']:.2f}")
    report.append("")
    report.append("---")
    report.append("")
    
    # Daily Breakdown
    report.append("## 📅 DAILY BREAKDOWN")
    report.append("")
    if week_data['by_day']:
        report.append("| Day | Date | Trades | Closed | P&L | Status |")
        report.append("|-----|------|--------|--------|-----|--------|")
        
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        for day_key in sorted(week_data['by_day'].keys()):
            try:
                date_obj = datetime.strptime(day_key, '%Y-%m-%d')
                day_name = days[date_obj.weekday()]
                data = week_data['by_day'][day_key]
                pnl = data['pnl']
                
                if date_obj.date() == today.date():
                    status = "🟢 **TODAY**"
                elif date_obj.date() < today.date():
                    status = "✅ Complete" if data['closed'] > 0 else "⏸️  No trades"
                else:
                    status = "📅 Upcoming"
                
                pnl_str = f"${pnl:,.2f}" if pnl != 0 else "$0.00"
                report.append(f"| {day_name} | {day_key} | {data['trades']} | {data['closed']} | {pnl_str} | {status} |")
            except:
                pass
    else:
        report.append("⚠️  No trading data for this week yet")
    report.append("")
    report.append("---")
    report.append("")
    
    # Strategy Performance
    report.append("## 🎯 STRATEGY PERFORMANCE THIS WEEK")
    report.append("")
    if week_data['by_strategy']:
        report.append("| Strategy | Trades | P&L | Win Rate |")
        report.append("|----------|--------|-----|----------|")
        for strategy, data in sorted(week_data['by_strategy'].items(), 
                                    key=lambda x: x[1]['pnl'], reverse=True):
            pnl_str = f"${data['pnl']:,.2f}" if data['pnl'] != 0 else "$0.00"
            win_rate_str = f"{data['win_rate']:.1f}%" if data['closed'] > 0 else "N/A"
            report.append(f"| {strategy} | {data['trades']} | {pnl_str} | {win_rate_str} |")
    report.append("")
    report.append("---")
    report.append("")
    
    # Pair Performance
    report.append("## 💱 PAIR PERFORMANCE THIS WEEK")
    report.append("")
    if week_data['by_pair']:
        report.append("| Pair | Trades | P&L | Win Rate |")
        report.append("|------|--------|-----|----------|")
        for pair, data in sorted(week_data['by_pair'].items(), 
                                key=lambda x: x[1]['pnl'], reverse=True):
            pnl_str = f"${data['pnl']:,.2f}" if data['pnl'] != 0 else "$0.00"
            win_rate_str = f"{data['win_rate']:.1f}%" if data['closed'] > 0 else "N/A"
            report.append(f"| {pair} | {data['trades']} | {pnl_str} | {win_rate_str} |")
    report.append("")
    
    return "\n".join(report)

def generate_weekly_roadmap(week_data: Dict, accounts_config: Dict) -> str:
    """Generate weekly roadmap"""
    report = []
    
    today = datetime.now()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    
    report.append("# 🗺️ WEEKLY ROADMAP")
    report.append(f"**Week:** {week_start.strftime('%B %d')} - {week_end.strftime('%B %d, %Y')}")
    report.append(f"**Generated:** {datetime.now().strftime('%B %d, %Y - %H:%M:%S')}")
    report.append("")
    report.append("---")
    report.append("")
    
    # Week Objectives
    report.append("## 🎯 WEEK OBJECTIVES")
    report.append("")
    
    days_remaining = (week_end - today).days + 1
    trades_so_far = week_data['total_trades']
    pnl_so_far = week_data['total_pnl']
    
    if trades_so_far > 0:
        avg_daily_trades = trades_so_far / max(days_remaining, 1)
        target_remaining = int(avg_daily_trades * days_remaining * 1.2)
        report.append(f"- **Target Remaining Trades:** {target_remaining}")
        report.append(f"- **Current P&L:** ${pnl_so_far:,.2f}")
        report.append(f"- **Target Week P&L:** ${abs(pnl_so_far) * 1.3:,.2f}")
    else:
        report.append("- **Target:** Establish baseline performance")
        report.append("- **Focus:** Consistent signal generation")
        report.append("- **Goal:** Begin building trade history")
    
    report.append("")
    report.append("---")
    report.append("")
    
    # Daily Roadmap
    report.append("## 📅 DAILY ROADMAP")
    report.append("")
    
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    for i in range(7):
        day_date = week_start + timedelta(days=i)
        day_name = days[i]
        
        if day_date.date() < today.date():
            status = "✅ Complete"
        elif day_date.date() == today.date():
            status = "🟢 **TODAY - ACTIVE**"
        else:
            status = "📅 Upcoming"
        
        day_key = day_date.strftime('%Y-%m-%d')
        day_data = week_data['by_day'].get(day_key, {'trades': 0, 'closed': 0, 'pnl': 0.0})
        
        report.append(f"### **{day_name}, {day_date.strftime('%B %d')}** - {status}")
        report.append("")
        
        if day_date.date() <= today.date():
            report.append(f"- **Trades:** {day_data['trades']}")
            report.append(f"- **P&L:** ${day_data['pnl']:,.2f}")
        else:
            # Plan for upcoming days
            if day_name in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
                report.append("- **Focus:** Active trading sessions")
                report.append("- **Target:** 3-5 quality signals")
                report.append("- **Best Times:** 1PM-5PM London (overlap)")
            else:
                report.append("- **Focus:** Market analysis")
                report.append("- **Target:** Strategy review")
                report.append("- **Best Times:** Plan for next week")
        
        report.append("")
    
    report.append("---")
    report.append("")
    
    # Strategy Focus
    report.append("## 🤖 STRATEGY FOCUS THIS WEEK")
    report.append("")
    
    if week_data['by_strategy']:
        for strategy, data in sorted(week_data['by_strategy'].items(), 
                                    key=lambda x: x[1]['pnl'], reverse=True):
            report.append(f"### **{strategy}**")
            report.append("")
            report.append(f"- **Current:** {data['trades']} trades, ${data['pnl']:,.2f} P&L")
            report.append("")
            
            if data['pnl'] > 0:
                report.append("✅ **Focus:** Continue strong performance")
            elif data['win_rate'] > 60:
                report.append("⚠️ **Focus:** Improve risk management")
            else:
                report.append("🔧 **Focus:** Strategy optimization")
            report.append("")
    else:
        report.append("📊 **All Strategies:** Focus on establishing baseline performance")
    
    report.append("---")
    report.append("")
    
    # Pair Focus
    report.append("## 💱 PAIR FOCUS THIS WEEK")
    report.append("")
    
    if week_data['by_pair']:
        for pair, data in sorted(week_data['by_pair'].items(), 
                                key=lambda x: x[1]['pnl'], reverse=True)[:5]:
            report.append(f"### **{pair}**")
            report.append("")
            report.append(f"- **Current:** {data['trades']} trades, ${data['pnl']:,.2f} P&L")
            report.append("")
            
            if data['pnl'] > 0:
                report.append("✅ **Priority:** High - Continue trading")
            elif data['win_rate'] > 55:
                report.append("⚠️ **Priority:** Medium - Optimize approach")
            else:
                report.append("🔧 **Priority:** Low - Review strategy")
            report.append("")
    else:
        report.append("📊 **All Pairs:** Monitor for opportunities")
    
    return "\n".join(report)

def main():
    """Main analysis function"""
    print("🚀 COMPREHENSIVE MONTHLY & WEEKLY PERFORMANCE ANALYSIS")
    print("=" * 60)
    print()
    
    # Load configuration
    print("📋 Loading configuration...")
    accounts_config = load_accounts_config()
    
    # Get database
    print("🔍 Locating database...")
    db_path = get_database_path()
    print(f"   Database: {db_path}")
    
    if not os.path.exists(db_path):
        print(f"⚠️  Database not found at {db_path}")
        print("   Creating analysis with available data...")
        db_path = None
    
    # Date ranges
    now = datetime.now()
    october_start = datetime(2025, 10, 1)
    october_end = datetime(2025, 10, 31, 23, 59, 59)
    
    # Current week
    week_start = now - timedelta(days=now.weekday())
    week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
    
    # Query data
    print("\n📊 Querying October data...")
    october_trades = []
    if db_path:
        october_trades = query_trades(db_path, october_start, october_end)
        print(f"   Found {len(october_trades)} trades in October")
    
    print("\n📊 Querying current week data...")
    week_trades = []
    if db_path:
        week_trades = query_trades(db_path, week_start, week_end)
        print(f"   Found {len(week_trades)} trades this week")
    
    # Analyze
    print("\n🔍 Analyzing data...")
    october_analysis = analyze_trades(october_trades)
    week_analysis = analyze_trades(week_trades)
    
    # Generate reports
    print("\n📝 Generating reports...")
    
    monthly_report = generate_monthly_report(october_analysis, accounts_config)
    monthly_roadmap = generate_monthly_roadmap(october_analysis, accounts_config)
    weekly_report = generate_weekly_report(week_analysis, accounts_config)
    weekly_roadmap = generate_weekly_roadmap(week_analysis, accounts_config)
    
    # Save reports
    output_dir = os.path.dirname(__file__)
    
    print("\n💾 Saving reports...")
    
    with open(os.path.join(output_dir, 'OCTOBER_2025_MONTHLY_ANALYSIS.md'), 'w') as f:
        f.write(monthly_report)
    print("   ✅ OCTOBER_2025_MONTHLY_ANALYSIS.md")
    
    with open(os.path.join(output_dir, 'NOVEMBER_2025_MONTHLY_ROADMAP.md'), 'w') as f:
        f.write(monthly_roadmap)
    print("   ✅ NOVEMBER_2025_MONTHLY_ROADMAP.md")
    
    with open(os.path.join(output_dir, 'WEEKLY_PERFORMANCE_BREAKDOWN.md'), 'w') as f:
        f.write(weekly_report)
    print("   ✅ WEEKLY_PERFORMANCE_BREAKDOWN.md")
    
    with open(os.path.join(output_dir, 'WEEKLY_ROADMAP.md'), 'w') as f:
        f.write(weekly_roadmap)
    print("   ✅ WEEKLY_ROADMAP.md")
    
    print("\n" + "=" * 60)
    print("✅ ANALYSIS COMPLETE!")
    print("\nGenerated Reports:")
    print("  1. OCTOBER_2025_MONTHLY_ANALYSIS.md - Full October breakdown")
    print("  2. NOVEMBER_2025_MONTHLY_ROADMAP.md - November plan")
    print("  3. WEEKLY_PERFORMANCE_BREAKDOWN.md - Current week analysis")
    print("  4. WEEKLY_ROADMAP.md - This week's plan")
    print()

if __name__ == "__main__":
    main()

