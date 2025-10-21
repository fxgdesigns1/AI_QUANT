#!/usr/bin/env python3
"""
Enhanced Scheduled Scanner Endpoints for Google Cloud Cron Jobs
Each function provides detailed context reports at specific times of day
"""

import os
import sys
import logging
from datetime import datetime, timedelta
import yaml
import pytz
import json

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load credentials
try:
    with open('app.yaml') as f:
        config = yaml.safe_load(f)
        os.environ['OANDA_API_KEY'] = config['env_variables']['OANDA_API_KEY']
    with open('accounts.yaml') as f:
        accounts = yaml.safe_load(f)
        os.environ['OANDA_ACCOUNT_ID'] = accounts['accounts'][0]['id']
    os.environ['TELEGRAM_TOKEN'] = "7248728383:AAEE7lkAAIUXBcK9iTPR5NIeTq3Aqbyx6IU"
    os.environ['TELEGRAM_CHAT_ID'] = "6100678501"
    logger.info("✅ Credentials loaded")
except Exception as e:
    logger.error(f"❌ Failed to load credentials: {e}")
    sys.exit(1)

# Import core modules
from src.core.oanda_client import OandaClient
from src.core.telegram_notifier import TelegramNotifier
from morning_scanner import scan_for_opportunities, send_opportunities_to_telegram

# Import contextual modules
try:
    from src.core.session_manager import get_session_manager
    from src.core.price_context_analyzer import get_price_context_analyzer
    from src.core.quality_scoring import get_quality_scoring
    from src.core.historical_news_fetcher import get_historical_news_fetcher
    logger.info("✅ Contextual modules imported")
except Exception as e:
    logger.error(f"❌ Failed to import contextual modules: {e}")
    sys.exit(1)


def get_key_levels_for_instruments(instruments):
    """Get key support/resistance levels for instruments"""
    client = OandaClient(
        os.environ['OANDA_API_KEY'],
        os.environ['OANDA_ACCOUNT_ID'],
        'practice'
    )
    price_analyzer = get_price_context_analyzer()
    
    key_levels = {}
    
    for instrument in instruments:
        try:
            # Get H4 data for key level detection
            result = client.get_candles(instrument, granularity='H4', count=100)
            if not result or 'candles' not in result:
                logger.warning(f"⚠️ No data for {instrument}")
                continue
                
            # Convert to DataFrame
            candles_data = []
            for c in result['candles']:
                if 'mid' in c:
                    candle_data = {
                        'open': float(c['mid']['o']),
                        'high': float(c['mid']['h']),
                        'low': float(c['mid']['l']),
                        'close': float(c['mid']['c']),
                        'volume': float(c.get('volume', 0))
                    }
                else:
                    candle_data = {
                        'open': float(c['bid']['o']),
                        'high': float(c['bid']['h']),
                        'low': float(c['bid']['l']),
                        'close': float(c['bid']['c']),
                        'volume': float(c.get('volume', 0))
                    }
                candles_data.append(candle_data)
                
            import pandas as pd
            df = pd.DataFrame(candles_data)
            
            # Get current price
            current_price = df['close'].iloc[-1]
            
            # Analyze price context with single timeframe
            price_data = {'H4': df}
            contexts = price_analyzer.analyze_price_context(instrument, price_data)
            trade_context = price_analyzer.get_trade_context(instrument, current_price, contexts)
            
            # Extract key levels
            nearest_support = trade_context.get('nearest_support')
            nearest_resistance = trade_context.get('nearest_resistance')
            
            key_levels[instrument] = {
                'current_price': current_price,
                'support': nearest_support,
                'resistance': nearest_resistance,
                'overall_trend': trade_context.get('overall_trend', 'neutral')
            }
            
            logger.info(f"✅ Key levels identified for {instrument}")
            
        except Exception as e:
            logger.error(f"❌ Error getting key levels for {instrument}: {e}")
    
    return key_levels


def get_economic_calendar():
    """Get economic calendar events for today and tomorrow"""
    news_fetcher = get_historical_news_fetcher()
    now = datetime.now(pytz.UTC)
    tomorrow = now + timedelta(days=1)
    
    # Get today's events
    today_events = news_fetcher.get_historical_news(from_date=now.replace(hour=0, minute=0, second=0),
                                                  to_date=now.replace(hour=23, minute=59, second=59))
    
    # Get tomorrow's events
    tomorrow_events = news_fetcher.get_historical_news(from_date=tomorrow.replace(hour=0, minute=0, second=0),
                                                     to_date=tomorrow.replace(hour=23, minute=59, second=59))
    
    # Filter for high impact events
    high_impact_today = []
    for currency, events in today_events.items():
        for event in events:
            if event.get('impact') == 'high':
                high_impact_today.append({
                    'currency': currency,
                    'time': event.get('time'),
                    'name': event.get('name')
                })
    
    high_impact_tomorrow = []
    for currency, events in tomorrow_events.items():
        for event in events:
            if event.get('impact') == 'high':
                high_impact_tomorrow.append({
                    'currency': currency,
                    'time': event.get('time'),
                    'name': event.get('name')
                })
    
    return {
        'today': high_impact_today,
        'tomorrow': high_impact_tomorrow
    }


def get_account_summary():
    """Get detailed account summary including open positions"""
    client = OandaClient(
        os.environ['OANDA_API_KEY'],
        os.environ['OANDA_ACCOUNT_ID'],
        'practice'
    )
    
    # Get account info
    account_info = client.get_account_info()
    
    # Get open positions
    positions = client.get_positions()
    
    # Format positions
    formatted_positions = []
    for position in positions:
        instrument = position.get('instrument')
        long_units = int(position.get('long', {}).get('units', 0))
        short_units = int(position.get('short', {}).get('units', 0))
        
        if long_units > 0:
            direction = "LONG"
            units = long_units
            entry_price = float(position.get('long', {}).get('averagePrice', 0))
            pl = float(position.get('long', {}).get('pl', 0))
            unrealized_pl = float(position.get('long', {}).get('unrealizedPL', 0))
        else:
            direction = "SHORT"
            units = abs(short_units)
            entry_price = float(position.get('short', {}).get('averagePrice', 0))
            pl = float(position.get('short', {}).get('pl', 0))
            unrealized_pl = float(position.get('short', {}).get('unrealizedPL', 0))
        
        formatted_positions.append({
            'instrument': instrument,
            'direction': direction,
            'units': units,
            'entry_price': entry_price,
            'pl': pl,
            'unrealized_pl': unrealized_pl
        })
    
    return {
        'balance': account_info.balance,
        'margin_used': account_info.margin_used,
        'margin_available': account_info.margin_available,
        'open_trade_count': account_info.open_trade_count,
        'positions': formatted_positions,
        'total_unrealized_pl': sum(p['unrealized_pl'] for p in formatted_positions)
    }


def pre_market_briefing():
    """6:00 AM - Enhanced pre-market briefing with market context"""
    logger.info("🌅 Generating pre-market briefing...")
    
    notifier = TelegramNotifier()
    session_manager = get_session_manager()
    
    # Get current session info
    now = datetime.now(pytz.UTC)
    london_time = now.astimezone(pytz.timezone('Europe/London'))
    session_quality, active_sessions = session_manager.get_session_quality(now)
    session_description = session_manager.get_session_description(now)
    
    # Get key market levels
    instruments = ['XAU_USD', 'EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'NZD_USD']
    key_levels = get_key_levels_for_instruments(instruments)
    
    # Get economic calendar
    calendar = get_economic_calendar()
    
    # Format economic events
    today_events_text = ""
    for event in calendar['today'][:5]:  # Show top 5 events
        time_str = event.get('time', '').split(' ')[1][:5]  # Extract HH:MM
        today_events_text += f"- {time_str} {event['currency']}: {event['name']}\n"
    
    if not today_events_text:
        today_events_text = "No major economic events today\n"
    
    # Format key levels
    levels_text = ""
    for instrument, data in key_levels.items():
        trend_emoji = "🔼" if data.get('overall_trend') == 'bullish' else "🔽" if data.get('overall_trend') == 'bearish' else "↔️"
        
        levels_text += f"{instrument} {trend_emoji}: "
        if data.get('support'):
            levels_text += f"S: {data['support']:.5f} "
        if data.get('resistance'):
            levels_text += f"R: {data['resistance']:.5f} "
        levels_text += f"(Now: {data['current_price']:.5f})\n"
    
    # Create message
    msg = f"""☕ **PRE-MARKET BRIEFING - {london_time.strftime('%A, %B %d')}**

**Session Status:**
{session_description} (Quality: {session_quality}/100)
London session opening soon

📰 **Economic Calendar Today:**
{today_events_text}

🎯 **Key Levels to Watch:**
{levels_text}

📈 **Market Context:**
- Overall: {'Bullish' if sum(1 for d in key_levels.values() if d.get('overall_trend') == 'bullish') > len(key_levels)/2 else 'Bearish' if sum(1 for d in key_levels.values() if d.get('overall_trend') == 'bearish') > len(key_levels)/2 else 'Mixed'} bias across instruments
- Volatility: {'Normal' if session_quality > 50 else 'Low'} expected

⏰ **Today's Schedule:**
- 8:00 AM: London Open Scan
- 1:00 PM: London/NY Overlap (Prime Trading)
- 5:00 PM: End of Day Summary"""
    
    notifier.send_system_status('Enhanced Pre-Market Briefing', msg)
    logger.info("✅ Pre-market briefing sent")
    return "Enhanced briefing sent"


def morning_scan():
    """8:00 AM - Enhanced London open scanner"""
    logger.info("🔍 Running enhanced morning scanner...")
    
    # Use the enhanced morning scanner
    opportunities = scan_for_opportunities()
    send_opportunities_to_telegram(opportunities)
    
    # Save to file with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    try:
        with open(f'morning_scan_{timestamp}.json', 'w') as f:
            json.dump(opportunities, f, indent=2, default=str)
        logger.info(f"✅ Morning scan results saved to morning_scan_{timestamp}.json")
    except Exception as e:
        logger.error(f"❌ Error saving scan results: {e}")
    
    return f"Enhanced morning scan: {len(opportunities)} opportunities"


def peak_scan():
    """1:00 PM - Enhanced London/NY overlap scanner with session context"""
    logger.info("🔍 Running peak time scanner (London/NY overlap)...")
    
    notifier = TelegramNotifier()
    session_manager = get_session_manager()
    
    # Get current session info
    now = datetime.now(pytz.UTC)
    session_quality, active_sessions = session_manager.get_session_quality(now)
    session_description = session_manager.get_session_description(now)
    
    # Check if we're in prime trading hours
    is_prime = session_manager.is_prime_trading_time(now)
    
    # Get opportunities
    opportunities = scan_for_opportunities()
    
    # Get account summary
    account = get_account_summary()
    
    # Format open positions
    positions_text = ""
    for pos in account['positions']:
        pl_emoji = "✅" if pos['unrealized_pl'] > 0 else "❌"
        positions_text += f"{pl_emoji} {pos['instrument']} {pos['direction']}: {pos['unrealized_pl']:.2f} USD\n"
    
    if not positions_text:
        positions_text = "No open positions\n"
    
    # Create message with context
    context_msg = f"""🎯 **PEAK TRADING HOURS SCAN - {now.astimezone(pytz.timezone('Europe/London')).strftime('%H:%M London')}**

**Session Status:**
{session_description} (Quality: {session_quality}/100)
{'✅ PRIME TRADING TIME' if is_prime else '⚠️ Not prime trading time'}

**Account Status:**
Balance: ${account['balance']:,.2f}
Open trades: {account['open_trade_count']}
Unrealized P/L: ${account['total_unrealized_pl']:,.2f}

**Open Positions:**
{positions_text}

**New Opportunities:**
{len(opportunities)} quality setups found during peak liquidity

{'[Details sent separately]' if opportunities else 'No new quality setups right now.'}

**Next Scan:** 5:00 PM (End of Day)"""
    
    notifier.send_system_status('Peak Time Market Context', context_msg)
    
    # Send opportunities if any
    if opportunities:
        send_opportunities_to_telegram(opportunities)
    
    # Save to file with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    try:
        with open(f'peak_scan_{timestamp}.json', 'w') as f:
            json.dump(opportunities, f, indent=2, default=str)
        logger.info(f"✅ Peak scan results saved to peak_scan_{timestamp}.json")
    except Exception as e:
        logger.error(f"❌ Error saving scan results: {e}")
    
    return f"Enhanced peak scan: {len(opportunities)} opportunities"


def eod_summary():
    """5:00 PM - Enhanced end of day summary with performance metrics"""
    logger.info("📊 Generating end of day summary...")
    
    notifier = TelegramNotifier()
    session_manager = get_session_manager()
    
    # Get current session info
    now = datetime.now(pytz.UTC)
    london_time = now.astimezone(pytz.timezone('Europe/London'))
    
    # Get account summary
    account = get_account_summary()
    
    # Get key market levels
    instruments = ['XAU_USD', 'EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'NZD_USD']
    key_levels = get_key_levels_for_instruments(instruments)
    
    # Get tomorrow's economic events
    calendar = get_economic_calendar()
    
    # Format tomorrow's events
    tomorrow_events_text = ""
    for event in calendar['tomorrow'][:5]:  # Show top 5 events
        time_str = event.get('time', '').split(' ')[1][:5]  # Extract HH:MM
        tomorrow_events_text += f"- {time_str} {event['currency']}: {event['name']}\n"
    
    if not tomorrow_events_text:
        tomorrow_events_text = "No major economic events tomorrow\n"
    
    # Format daily performance
    daily_performance = ""
    for instrument, data in key_levels.items():
        # Calculate daily change (would need to store previous day's close)
        # For now, just show current price
        daily_performance += f"{instrument}: {data['current_price']:.5f}\n"
    
    # Format open positions
    positions_text = ""
    for pos in account['positions']:
        pl_emoji = "✅" if pos['unrealized_pl'] > 0 else "❌"
        positions_text += f"{pl_emoji} {pos['instrument']} {pos['direction']}: {pos['unrealized_pl']:.2f} USD\n"
    
    if not positions_text:
        positions_text = "No open positions\n"
    
    # Create message
    msg = f"""📊 **ENHANCED END OF DAY REVIEW - {london_time.strftime('%A, %B %d')}**

**Account Status:**
Balance: ${account['balance']:,.2f}
Open trades: {account['open_trade_count']}
Unrealized P/L: ${account['total_unrealized_pl']:,.2f}

**Open Positions:**
{positions_text}

**Daily Performance:**
{daily_performance}

**Tomorrow's Key Events:**
{tomorrow_events_text}

**Market Status:**
London session closed
NY session winding down
{'Consider closing day trades' if account['open_trade_count'] > 0 else 'No open positions to manage'}

⏰ **Next Alert:** Tomorrow 6:00 AM Pre-Market Briefing"""
    
    notifier.send_system_status('Enhanced End of Day Summary', msg)
    logger.info("✅ EOD summary sent")
    return "Enhanced EOD summary sent"


def asian_preview():
    """9:00 PM - Enhanced Asian session preview with overnight context"""
    logger.info("🌙 Generating Asian session preview...")
    
    notifier = TelegramNotifier()
    session_manager = get_session_manager()
    
    # Get current session info
    now = datetime.now(pytz.UTC)
    session_quality, active_sessions = session_manager.get_session_quality(now)
    session_description = session_manager.get_session_description(now)
    
    # Get key market levels for Asian-relevant pairs
    instruments = ['XAU_USD', 'USD_JPY', 'AUD_USD', 'NZD_USD']
    key_levels = get_key_levels_for_instruments(instruments)
    
    # Get account summary
    account = get_account_summary()
    
    # Format key levels
    levels_text = ""
    for instrument, data in key_levels.items():
        trend_emoji = "🔼" if data.get('overall_trend') == 'bullish' else "🔽" if data.get('overall_trend') == 'bearish' else "↔️"
        
        levels_text += f"{instrument} {trend_emoji}: "
        if data.get('support'):
            levels_text += f"S: {data['support']:.5f} "
        if data.get('resistance'):
            levels_text += f"R: {data['resistance']:.5f} "
        levels_text += f"(Now: {data['current_price']:.5f})\n"
    
    # Format open positions
    positions_text = ""
    for pos in account['positions']:
        pl_emoji = "✅" if pos['unrealized_pl'] > 0 else "❌"
        positions_text += f"{pl_emoji} {pos['instrument']} {pos['direction']}: {pos['unrealized_pl']:.2f} USD\n"
    
    if not positions_text:
        positions_text = "No open positions\n"
    
    # Create message
    msg = f"""🌙 **ENHANCED ASIAN SESSION PREVIEW - {now.astimezone(pytz.timezone('Europe/London')).strftime('%A %H:%M')}**

**Session Status:**
{session_description} (Quality: {session_quality}/100)
Sydney, Tokyo sessions ahead

**Account Status:**
Balance: ${account['balance']:,.2f}
Open trades: {account['open_trade_count']}
Unrealized P/L: ${account['total_unrealized_pl']:,.2f}

**Open Positions:**
{positions_text}

**Key Levels for Asian Session:**
{levels_text}

**Trading Recommendation:**
- Lower liquidity during Asian session
- {'Consider trailing stops on open positions' if account['open_trade_count'] > 0 else 'No positions to manage'}
- Best to wait for London open (8 AM tomorrow)

⏰ **Next Alert:** Tomorrow 6:00 AM Pre-Market Briefing"""
    
    notifier.send_system_status('Enhanced Asian Session Preview', msg)
    logger.info("✅ Asian preview sent")
    return "Enhanced Asian preview sent"


def continuous_monitor():
    """Every 15 minutes - Enhanced market monitor with alerts for significant moves"""
    logger.info("🔍 Running continuous market monitor...")
    
    client = OandaClient(
        os.environ['OANDA_API_KEY'],
        os.environ['OANDA_ACCOUNT_ID'],
        'practice'
    )
    notifier = TelegramNotifier()
    session_manager = get_session_manager()
    
    # Get current session info
    now = datetime.now(pytz.UTC)
    session_quality, active_sessions = session_manager.get_session_quality(now)
    
    # Instruments to monitor
    instruments = ['XAU_USD', 'EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'NZD_USD']
    
    # Load previous prices (if available)
    previous_prices = {}
    try:
        if os.path.exists('previous_prices.json'):
            with open('previous_prices.json', 'r') as f:
                previous_prices = json.load(f)
    except Exception as e:
        logger.error(f"❌ Error loading previous prices: {e}")
    
    # Get current prices
    current_prices = {}
    significant_moves = []
    
    for instrument in instruments:
        try:
            result = client.get_candles(instrument, granularity='M5', count=1)
            if result and 'candles' in result and len(result['candles']) > 0:
                candle = result['candles'][0]
                if 'mid' in candle:
                    price = float(candle['mid']['c'])
                else:
                    price = float(candle['bid']['c'])
                
                current_prices[instrument] = price
                
                # Check for significant moves (>0.3% in 15 minutes)
                if instrument in previous_prices:
                    prev_price = previous_prices[instrument]
                    pct_change = (price - prev_price) / prev_price * 100
                    
                    if abs(pct_change) > 0.3:
                        direction = "UP" if pct_change > 0 else "DOWN"
                        significant_moves.append({
                            'instrument': instrument,
                            'price': price,
                            'change': pct_change,
                            'direction': direction
                        })
        except Exception as e:
            logger.error(f"❌ Error getting price for {instrument}: {e}")
    
    # Save current prices for next check
    try:
        with open('previous_prices.json', 'w') as f:
            json.dump(current_prices, f)
    except Exception as e:
        logger.error(f"❌ Error saving current prices: {e}")
    
    # Send alert if significant moves detected
    if significant_moves:
        moves_text = ""
        for move in significant_moves:
            direction_emoji = "🔼" if move['direction'] == "UP" else "🔽"
            moves_text += f"{direction_emoji} {move['instrument']}: {move['change']:.2f}% ({move['price']:.5f})\n"
        
        msg = f"""⚠️ **SIGNIFICANT MARKET MOVES DETECTED**

The following instruments have moved >0.3% in the last 15 minutes:

{moves_text}

**Session:** {session_manager.get_session_description(now)}
**Time:** {now.astimezone(pytz.timezone('Europe/London')).strftime('%H:%M London')}

Consider checking charts for trading opportunities."""
        
        notifier.send_system_status('Market Movement Alert', msg)
        logger.info(f"✅ Significant moves alert sent: {len(significant_moves)} instruments")
        return f"Alert sent: {len(significant_moves)} significant moves"
    
    logger.info("✅ Continuous monitor completed - no significant moves")
    return "Monitoring active - no significant moves"


if __name__ == '__main__':
    # Test all functions
    logger.info("Testing all scheduled functions...\n")
    
    logger.info("1. Pre-Market Briefing:")
    result = pre_market_briefing()
    logger.info(result)
    
    logger.info("\n2. Morning Scan:")
    result = morning_scan()
    logger.info(result)
    
    logger.info("\n3. Peak Scan:")
    result = peak_scan()
    logger.info(result)
    
    logger.info("\n4. EOD Summary:")
    result = eod_summary()
    logger.info(result)
    
    logger.info("\n5. Asian Preview:")
    result = asian_preview()
    logger.info(result)
    
    logger.info("\n6. Continuous Monitor:")
    result = continuous_monitor()
    logger.info(result)
    
    logger.info("\n✅ All enhanced functions tested!")