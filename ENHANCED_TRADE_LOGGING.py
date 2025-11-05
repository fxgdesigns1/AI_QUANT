#!/usr/bin/env python3
"""
ENHANCED TRADE LOGGING - Add detailed logging to understand why trades aren't executing
This patches the trading system to add comprehensive logging
"""
import sys
import os

# Monkey patch to add detailed logging
def add_enhanced_logging():
    """Add enhanced logging to understand trade execution flow"""
    
    # Patch ai_trading_system.py if it exists
    if os.path.exists('ai_trading_system.py'):
        with open('ai_trading_system.py', 'r') as f:
            content = f.read()
        
        # Check if already patched
        if 'ENHANCED_LOGGING_PATCH' in content:
            print("✓ Enhanced logging already patched")
            return
        
        # Add logging to execute_trade method
        patches = []
        
        # Patch 1: Log why trades are blocked
        old_check = "if not self.trading_enabled:\n                return False"
        new_check = """if not self.trading_enabled:
                logger.info("🚫 TRADE BLOCKED: Trading disabled")
                return False"""
        
        if old_check in content:
            content = content.replace(old_check, new_check)
            patches.append("Trading enabled check")
        
        # Patch 2: Log news halt
        old_news = "if self.is_news_halt_active():\n                logger.info(\"News halt active; skipping new entry\")\n                return False"
        new_news = """if self.is_news_halt_active():
                halt_until = self.news_halt_until.strftime('%H:%M:%S UTC') if self.news_halt_until else 'unknown'
                logger.info(f"🚫 TRADE BLOCKED: News halt active until {halt_until}")
                return False"""
        
        if old_news in content:
            content = content.replace(old_news, new_news)
            patches.append("News halt check")
        
        # Patch 3: Log daily limit
        old_daily = "if self.daily_trade_count >= self.max_daily_trades:\n                logger.warning(\"Daily trade limit reached\")\n                return False"
        new_daily = """if self.daily_trade_count >= self.max_daily_trades:
                logger.warning(f"🚫 TRADE BLOCKED: Daily limit reached ({self.daily_trade_count}/{self.max_daily_trades})")
                return False"""
        
        if old_daily in content:
            content = content.replace(old_daily, new_daily)
            patches.append("Daily limit check")
        
        # Patch 4: Log concurrent trades
        old_concurrent = "if total_live >= self.max_concurrent_trades:\n                logger.info(\"Global cap reached (positions+pending); skipping new entry\")\n                return False"
        new_concurrent = """if total_live >= self.max_concurrent_trades:
                logger.info(f"🚫 TRADE BLOCKED: Global cap reached ({total_live}/{self.max_concurrent_trades} - positions:{live['positions']}, pending:{live['pending']})")
                return False"""
        
        if old_concurrent in content:
            content = content.replace(old_concurrent, new_concurrent)
            patches.append("Concurrent trades check")
        
        # Patch 5: Log per-symbol cap
        old_symbol = "if sym_live >= current_symbol_cap or current_symbol_count >= current_symbol_cap:\n                logger.info(f\"Skipping trade: per-symbol cap reached for {current_symbol}\")\n                return False"
        new_symbol = """if sym_live >= current_symbol_cap or current_symbol_count >= current_symbol_cap:
                logger.info(f"🚫 TRADE BLOCKED: Per-symbol cap reached for {current_symbol} (live:{sym_live}, tracked:{current_symbol_count}, cap:{current_symbol_cap})")
                return False"""
        
        if old_symbol in content:
            content = content.replace(old_symbol, new_symbol)
            patches.append("Per-symbol cap check")
        
        # Patch 6: Log signal generation details
        old_signals = "signals = self.analyze_market(prices)\n        logger.info(f\"📊 Generated {len(signals)} trading signals\")"
        new_signals = """signals = self.analyze_market(prices)
        logger.info(f"📊 Generated {len(signals)} trading signals")
        if len(signals) == 0:
            logger.info("🔍 No signals generated - checking reasons:")
            if not prices:
                logger.info("  • No price data available")
            else:
                logger.info(f"  • Price data available for {len(prices)} instruments")
                for inst, price_data in prices.items():
                    spread = price_data.get('spread', 0)
                    max_spread = self.instrument_spread_limits.get(inst, 0.00030)
                    if spread > max_spread:
                        logger.info(f"  • {inst}: Spread too wide ({spread:.5f} > {max_spread:.5f})")
                    if self.is_news_halt_active():
                        logger.info(f"  • {inst}: News halt active")
                    if inst == 'XAU_USD' and not self.in_london_session():
                        logger.info(f"  • {inst}: Outside London session")
        else:
            for sig in signals:
                logger.info(f"  ✓ Signal: {sig['instrument']} {sig['side']} @ {sig['entry_price']:.5f} (confidence: {sig['confidence']})")"""
        
        if old_signals in content:
            content = content.replace(old_signals, new_signals)
            patches.append("Signal generation logging")
        
        # Add marker
        content = "# ENHANCED_LOGGING_PATCH v1.0\n" + content
        
        if patches:
            # Backup original
            import shutil
            shutil.copy('ai_trading_system.py', 'ai_trading_system.py.backup')
            
            # Write patched version
            with open('ai_trading_system.py', 'w') as f:
                f.write(content)
            
            print(f"✅ Enhanced logging patched: {', '.join(patches)}")
            print("  • Backup saved to: ai_trading_system.py.backup")
        else:
            print("⚠ No patches applied (patterns not found)")
    else:
        print("❌ ai_trading_system.py not found")

if __name__ == "__main__":
    add_enhanced_logging()
