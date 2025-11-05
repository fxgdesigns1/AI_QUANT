#!/usr/bin/env python3
"""
COMPREHENSIVE TRADE DIAGNOSTIC
Identifies ALL reasons why trades aren't executing
"""
import os
import sys
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import the trading system
try:
    from ai_trading_system import AITradingSystem
except Exception as e:
    logger.error(f"Failed to import AITradingSystem: {e}")
    AITradingSystem = None

class TradeDiagnostic:
    def __init__(self):
        self.system = None
        self.issues = []
        self.warnings = []
        self.info = []
        
    def run_full_diagnostic(self):
        """Run complete diagnostic"""
        print("="*80)
        print("🔍 COMPREHENSIVE TRADE DIAGNOSTIC")
        print("="*80)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print()
        
        if not AITradingSystem:
            print("❌ CRITICAL: Cannot import AITradingSystem")
            return
        
        try:
            self.system = AITradingSystem()
        except Exception as e:
            print(f"❌ CRITICAL: Failed to initialize system: {e}")
            return
        
        # Run all diagnostic checks
        self.check_trading_enabled()
        self.check_news_halts()
        self.check_sentiment_throttle()
        self.check_market_hours()
        self.check_price_data()
        self.check_strategy_criteria()
        self.check_position_limits()
        self.check_daily_limits()
        self.check_spread_conditions()
        self.check_weekend_mode()
        self.check_monday_recovery()
        
        # Generate report
        self.generate_report()
        
    def check_trading_enabled(self):
        """Check if trading is enabled"""
        print("\n[CHECK 1] Trading Enabled Status")
        print("-"*80)
        
        if not self.system.trading_enabled:
            self.issues.append("❌ Trading is DISABLED - Set to False")
            print("❌ Trading is DISABLED")
            print("   Fix: Use /start_trading command or set trading_enabled = True")
        else:
            self.info.append("✅ Trading is ENABLED")
            print("✅ Trading is ENABLED")
    
    def check_news_halts(self):
        """Check news halt status"""
        print("\n[CHECK 2] News Halt Status")
        print("-"*80)
        
        if self.system.is_news_halt_active():
            halt_until = self.system.news_halt_until
            now = datetime.utcnow()
            
            if halt_until and halt_until > now:
                time_remaining = (halt_until - now).total_seconds() / 60
                self.issues.append(f"❌ News halt ACTIVE - Blocks trades for {time_remaining:.1f} more minutes")
                print(f"❌ News halt ACTIVE")
                print(f"   Until: {halt_until.strftime('%Y-%m-%d %H:%M:%S UTC')}")
                print(f"   Time remaining: {time_remaining:.1f} minutes")
                print(f"   Fix: Wait for expiry or manually clear: system.news_halt_until = None")
            else:
                # Stale halt - should be cleared
                self.warnings.append("⚠️ Stale news halt detected (should be cleared)")
                print("⚠️ Stale news halt (should be cleared)")
        else:
            self.info.append("✅ No news halt active")
            print("✅ No news halt active")
    
    def check_sentiment_throttle(self):
        """Check sentiment throttle"""
        print("\n[CHECK 3] Sentiment Throttle Status")
        print("-"*80)
        
        if self.system.is_throttle_active():
            throttle_until = self.system.throttle_until
            now = datetime.utcnow()
            
            if throttle_until and throttle_until > now:
                time_remaining = (throttle_until - now).total_seconds() / 60
                self.issues.append(f"❌ Sentiment throttle ACTIVE - Blocks trades for {time_remaining:.1f} more minutes")
                print(f"❌ Sentiment throttle ACTIVE")
                print(f"   Until: {throttle_until.strftime('%Y-%m-%d %H:%M:%S UTC')}")
                print(f"   Time remaining: {time_remaining:.1f} minutes")
                print(f"   Risk reduced to: {self.system.risk_per_trade*100:.1f}%")
                print(f"   Fix: Wait for expiry or manually clear: system.throttle_until = None")
            else:
                self.warnings.append("⚠️ Stale sentiment throttle detected")
                print("⚠️ Stale sentiment throttle (should be cleared)")
        else:
            self.info.append("✅ No sentiment throttle active")
            print("✅ No sentiment throttle active")
    
    def check_market_hours(self):
        """Check market hours and session restrictions"""
        print("\n[CHECK 4] Market Hours & Session Restrictions")
        print("-"*80)
        
        now = datetime.utcnow()
        hour = now.hour
        weekday = now.weekday()  # 0=Monday, 6=Sunday
        
        # Check if weekend
        if weekday >= 5:
            self.issues.append("❌ It's WEEKEND - Markets closed")
            print(f"❌ It's WEEKEND (Day {weekday})")
            print("   Forex markets closed Friday 22:00 UTC - Sunday 22:00 UTC")
        else:
            print(f"✅ It's a WEEKDAY (Day {weekday})")
        
        # Check London session
        in_london = self.system.in_london_session()
        in_overlap = self.system.in_london_overlap()
        
        print(f"   Current UTC hour: {hour}")
        print(f"   London session (8-17 UTC): {'✅ YES' if in_london else '❌ NO'}")
        print(f"   London/NY overlap (13-17 UTC): {'✅ YES' if in_overlap else '❌ NO'}")
        
        # XAU session restriction
        if not in_london:
            self.issues.append("❌ Outside London session - XAU_USD trades BLOCKED")
            print("   ⚠️ XAU_USD trades require London session (8-17 UTC)")
            print("   This blocks ALL gold trades outside these hours")
        else:
            self.info.append("✅ London session active - XAU trades allowed")
    
    def check_price_data(self):
        """Check if price data is available"""
        print("\n[CHECK 5] Price Data Availability")
        print("-"*80)
        
        try:
            prices = self.system.get_current_prices()
            
            if not prices:
                self.issues.append("❌ NO price data available - Cannot trade")
                print("❌ NO price data available")
                print("   Fix: Check OANDA API connection and account status")
                return
            
            print(f"✅ Price data available for {len(prices)} instruments")
            
            # Check each instrument
            for inst in self.system.instruments:
                if inst in prices:
                    price_data = prices[inst]
                    spread = price_data.get('spread', 0)
                    max_spread = self.system.instrument_spread_limits.get(inst, 0.00030)
                    
                    if spread > max_spread:
                        self.issues.append(f"❌ {inst} spread too wide: {spread:.5f} > {max_spread:.5f}")
                        print(f"   ❌ {inst}: Spread {spread:.5f} > limit {max_spread:.5f}")
                    else:
                        print(f"   ✅ {inst}: Spread {spread:.5f} OK")
                else:
                    self.issues.append(f"❌ {inst} price data MISSING")
                    print(f"   ❌ {inst}: Price data missing")
                    
        except Exception as e:
            self.issues.append(f"❌ Error getting prices: {e}")
            print(f"❌ Error getting prices: {e}")
    
    def check_strategy_criteria(self):
        """Check if strategy criteria are too strict"""
        print("\n[CHECK 6] Strategy Criteria")
        print("-"*80)
        
        try:
            prices = self.system.get_current_prices()
            if not prices:
                print("⚠️ Cannot check criteria - no price data")
                return
            
            # Try to generate signals
            signals = self.system.analyze_market(prices)
            
            if not signals:
                self.warnings.append("⚠️ No signals generated - Strategy criteria may be too strict")
                print("⚠️ No signals generated")
                print("   Possible reasons:")
                print("   - EMA/ATR criteria too strict")
                print("   - confirm_above/confirm_below requirements not met")
                print("   - slope_up requirement not met")
                print("   - M15 EMA alignment requirement not met")
                print("   - Spread too wide")
                print("   - Outside London session (for XAU)")
            else:
                print(f"✅ Generated {len(signals)} signals")
                for sig in signals[:3]:
                    print(f"   • {sig['instrument']} {sig['side']} - Confidence: {sig['confidence']}")
                    
        except Exception as e:
            self.warnings.append(f"⚠️ Error checking strategy: {e}")
            print(f"⚠️ Error checking strategy: {e}")
    
    def check_position_limits(self):
        """Check position limits"""
        print("\n[CHECK 7] Position Limits")
        print("-"*80)
        
        try:
            live = self.system.get_live_counts()
            total_live = live['positions'] + live['pending']
            
            print(f"   Active positions: {live['positions']}")
            print(f"   Pending orders: {live['pending']}")
            print(f"   Total live: {total_live}/{self.system.max_concurrent_trades}")
            
            if total_live >= self.system.max_concurrent_trades:
                self.issues.append(f"❌ Position limit reached: {total_live}/{self.system.max_concurrent_trades}")
                print(f"❌ Position limit REACHED")
                print(f"   Fix: Close some positions or increase max_concurrent_trades")
            else:
                print(f"✅ Position limit OK ({total_live} < {self.system.max_concurrent_trades})")
                
            # Check per-symbol limits
            for inst in self.system.instruments:
                count = live['by_symbol'].get(inst, 0)
                cap = self.system.per_symbol_cap.get(inst, self.system.max_per_symbol)
                if count >= cap:
                    self.issues.append(f"❌ {inst} symbol limit reached: {count}/{cap}")
                    print(f"   ❌ {inst}: {count}/{cap} limit reached")
                else:
                    print(f"   ✅ {inst}: {count}/{cap} OK")
                    
        except Exception as e:
            self.warnings.append(f"⚠️ Error checking positions: {e}")
            print(f"⚠️ Error checking positions: {e}")
    
    def check_daily_limits(self):
        """Check daily trade limits"""
        print("\n[CHECK 8] Daily Trade Limits")
        print("-"*80)
        
        print(f"   Daily trades: {self.system.daily_trade_count}/{self.system.max_daily_trades}")
        
        if self.system.daily_trade_count >= self.system.max_daily_trades:
            self.issues.append(f"❌ Daily trade limit reached: {self.system.daily_trade_count}/{self.system.max_daily_trades}")
            print(f"❌ Daily limit REACHED")
            print(f"   Fix: Wait for reset or increase max_daily_trades")
        else:
            print(f"✅ Daily limit OK")
    
    def check_spread_conditions(self):
        """Check spread conditions"""
        print("\n[CHECK 9] Spread Conditions")
        print("-"*80)
        
        try:
            prices = self.system.get_current_prices()
            if not prices:
                return
            
            for inst in self.system.instruments:
                if inst in prices:
                    spread = prices[inst]['spread']
                    max_spread = self.system.instrument_spread_limits.get(inst, 0.00030)
                    
                    # XAU has special spread check during non-overlap
                    if inst == 'XAU_USD' and not self.system.in_london_overlap():
                        max_spread = min(max_spread, 0.60)
                    
                    if spread > max_spread:
                        self.issues.append(f"❌ {inst} spread too wide: {spread:.5f} > {max_spread:.5f}")
                        print(f"   ❌ {inst}: {spread:.5f} > {max_spread:.5f}")
                    else:
                        print(f"   ✅ {inst}: {spread:.5f} <= {max_spread:.5f}")
                        
        except Exception as e:
            print(f"⚠️ Error checking spreads: {e}")
    
    def check_weekend_mode(self):
        """Check weekend mode"""
        print("\n[CHECK 10] Weekend Mode")
        print("-"*80)
        
        weekend_mode = os.getenv('WEEKEND_MODE', 'false').lower() == 'true'
        
        if weekend_mode:
            self.issues.append("❌ WEEKEND_MODE environment variable is 'true' - Trading disabled")
            print("❌ WEEKEND_MODE=true")
            print("   Fix: Set WEEKEND_MODE=false or unset the variable")
        else:
            print("✅ WEEKEND_MODE not enabled")
    
    def check_monday_recovery(self):
        """Check Monday morning recovery"""
        print("\n[CHECK 11] Monday Morning Recovery")
        print("-"*80)
        
        now = datetime.utcnow()
        weekday = now.weekday()  # 0=Monday
        
        if weekday == 0:  # Monday
            hour = now.hour
            print(f"✅ It's MONDAY (Hour {hour} UTC)")
            
            # Check if news halt is stale (from weekend)
            if self.system.news_halt_until:
                halt_age = (now - self.system.news_halt_until).total_seconds() / 3600
                if halt_age > 2:  # More than 2 hours old
                    self.warnings.append("⚠️ Stale news halt from weekend detected - should be cleared")
                    print("⚠️ Stale news halt detected (may be from weekend)")
                    print("   Fix: Clear stale halts on Monday morning")
            
            # Check if throttle is stale
            if self.system.throttle_until:
                throttle_age = (now - self.system.throttle_until).total_seconds() / 3600
                if throttle_age > 2:
                    self.warnings.append("⚠️ Stale sentiment throttle from weekend detected")
                    print("⚠️ Stale sentiment throttle detected")
        else:
            print(f"   Not Monday (Day {weekday})")
    
    def generate_report(self):
        """Generate final diagnostic report"""
        print("\n" + "="*80)
        print("📊 DIAGNOSTIC SUMMARY")
        print("="*80)
        
        # Critical issues
        if self.issues:
            print(f"\n❌ CRITICAL ISSUES ({len(self.issues)}):")
            for i, issue in enumerate(self.issues, 1):
                print(f"   {i}. {issue}")
        else:
            print("\n✅ No critical issues found")
        
        # Warnings
        if self.warnings:
            print(f"\n⚠️ WARNINGS ({len(self.warnings)}):")
            for i, warning in enumerate(self.warnings, 1):
                print(f"   {i}. {warning}")
        else:
            print("\n✅ No warnings")
        
        # Info
        if self.info:
            print(f"\n✅ OPERATIONAL CHECKS ({len(self.info)}):")
            for i, info in enumerate(self.info[:5], 1):
                print(f"   {i}. {info}")
        
        # Recommendations
        print("\n" + "="*80)
        print("💡 RECOMMENDATIONS")
        print("="*80)
        
        if self.issues:
            print("\nIMMEDIATE FIXES NEEDED:")
            
            if any("Trading is DISABLED" in i for i in self.issues):
                print("\n1. Enable Trading:")
                print("   - Send Telegram: /start_trading")
                print("   - Or: system.trading_enabled = True")
            
            if any("News halt" in i for i in self.issues):
                print("\n2. Clear News Halt:")
                print("   - system.news_halt_until = None")
                print("   - Or wait for expiry")
            
            if any("Sentiment throttle" in i for i in self.issues):
                print("\n3. Clear Sentiment Throttle:")
                print("   - system.throttle_until = None")
            
            if any("WEEKEND" in i for i in self.issues):
                print("\n4. Weekend Mode:")
                print("   - Wait for markets to open (Sunday 22:00 UTC)")
                print("   - Or disable weekend mode: WEEKEND_MODE=false")
            
            if any("London session" in i for i in self.issues):
                print("\n5. London Session:")
                print("   - Wait for London session (8-17 UTC)")
                print("   - Or remove London session restriction for XAU")
            
            if any("spread too wide" in i for i in self.issues):
                print("\n6. Spread Issues:")
                print("   - Wait for tighter spreads")
                print("   - Or increase spread limits")
            
            if any("limit reached" in i for i in self.issues):
                print("\n7. Position Limits:")
                print("   - Close some positions")
                print("   - Or increase limits")
        else:
            print("\n✅ No immediate fixes needed")
            print("\nIf still no trades, check:")
            print("   - Strategy criteria may be too strict")
            print("   - Market conditions may not meet entry criteria")
            print("   - Wait for better trading opportunities")
        
        print("\n" + "="*80)
        print("✅ DIAGNOSTIC COMPLETE")
        print("="*80)

def main():
    diagnostic = TradeDiagnostic()
    diagnostic.run_full_diagnostic()

if __name__ == "__main__":
    main()
