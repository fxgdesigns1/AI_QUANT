#!/usr/bin/env python3
"""Display weekly roadmaps for all strategy/pair combinations"""

import sys
sys.path.insert(0, 'google-cloud-trading-system/src')

from core.trump_dna_framework import get_trump_dna_planner
from datetime import datetime

def main():
    print("=" * 80)
    print("📅 WEEKLY TRADING ROADMAPS - TRUMP DNA")
    print(f"Week of: {datetime.now().strftime('%B %d, 2025')}")
    print("=" * 80)
    print()
    
    planner = get_trump_dna_planner()
    
    total_weekly = 0
    
    for plan_key, plan in planner.weekly_plans.items():
        total_weekly += plan.weekly_target_dollars
        
        print(f"{'─' * 80}")
        print(f"📊 {plan.pair} - {plan.strategy_name}")
        print(f"{'─' * 80}")
        print()
        
        # Weekly target
        print(f"💰 WEEKLY TARGET: ${plan.weekly_target_dollars:,.0f}")
        print()
        
        # Daily breakdown
        print("📅 DAILY TARGETS:")
        for day, target in plan.daily_targets.items():
            emoji = "🔥" if target >= 600 else "📈" if target >= 400 else "📊"
            print(f"   {emoji} {day:12s}: ${target:>6.0f}")
        print()
        
        # Key events
        if plan.key_events:
            print("🗓️  KEY EVENTS THIS WEEK:")
            for event in plan.key_events:
                impact_emoji = "🔥" if event['impact'] == 'EXTREME' else "⚡" if event['impact'] == 'HIGH' else "📊"
                print(f"   {impact_emoji} {event['day']:12s} {event['time']}: {event['event']}")
            print()
        
        # Sniper setup
        print(f"🎯 SNIPER SETUP:")
        print(f"   Stop Loss: {plan.stop_loss_pips} pips (TIGHT & FIXED)")
        print(f"   Take Profit: {plan.take_profit_pips} pips (CLEAR TARGET)")
        print(f"   Risk/Reward: 1:{plan.take_profit_pips/plan.stop_loss_pips:.1f}")
        print(f"   Max Trades/Day: {plan.max_trades_per_day} (SELECTIVE)")
        print(f"   Max Hold: {plan.max_hold_hours} hours (QUICK EXIT)")
        print()
        
        # Entry zones
        print(f"📍 ENTRY ZONES (Sniper Levels):")
        for zone in plan.entry_zones:
            action_emoji = "🟢" if zone['action'] == 'BUY' else "🔴"
            if 'XAU' in plan.pair:
                print(f"   {action_emoji} ${zone['level']:.2f} ({zone['type']}) → {zone['action']}")
            else:
                print(f"   {action_emoji} {zone['level']:.5f} ({zone['type']}) → {zone['action']}")
        print()
        
        # Market roadmap
        print(f"🗺️  WEEK'S ROADMAP:")
        print(f"   Trend: {plan.trend_direction}")
        print(f"   Volatility: {plan.volatility_forecast}")
        print(f"   Best Days: {', '.join(plan.best_trading_days)}")
        print()
        
        # Support/Resistance
        print(f"📊 KEY LEVELS:")
        if 'XAU' in plan.pair:
            print(f"   Support: {' | '.join([f'${s:.0f}' for s in plan.support_levels])}")
            print(f"   Resistance: {' | '.join([f'${r:.0f}' for r in plan.resistance_levels])}")
        else:
            print(f"   Support: {' | '.join([f'{s:.5f}' for s in plan.support_levels])}")
            print(f"   Resistance: {' | '.join([f'{r:.5f}' for r in plan.resistance_levels])}")
        print()
    
    print("=" * 80)
    print(f"💰 TOTAL WEEKLY TARGET (ALL STRATEGIES): ${total_weekly:,.0f}")
    print("=" * 80)
    print()
    
    # Show today's plan
    today = datetime.now().strftime('%A')
    print(f"🎯 TODAY ({today.upper()}) - FOCUS PAIRS:")
    print("=" * 80)
    
    for plan_key, plan in planner.weekly_plans.items():
        daily_target = plan.daily_targets.get(today, 0)
        events_today = [e for e in plan.key_events if e['day'] == today]
        
        if daily_target > 0 or events_today:
            emoji = "🔥" if daily_target >= 600 else "📈" if daily_target >= 400 else "📊"
            print(f"{emoji} {plan.pair:12s} - ${daily_target:>6.0f} target", end='')
            
            if events_today:
                print(f" | Event: {events_today[0]['event']}", end='')
            print()
    
    print("=" * 80)

if __name__ == "__main__":
    main()



