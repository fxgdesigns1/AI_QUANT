#!/usr/bin/env python3
"""
ENHANCED MORNING OPPORTUNITY SCANNER
Runs at 8:00 AM London time (or on demand)
Finds 3-5 HIGH QUALITY setups for the day using contextual analysis
"""

import os
import sys
from datetime import datetime
import yaml
import pandas as pd
import logging
import pytz

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

sys.path.insert(0, '.')

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

# Import contextual modules
try:
    from src.core.session_manager import get_session_manager
    from src.core.price_context_analyzer import get_price_context_analyzer
    from src.core.quality_scoring import get_quality_scoring, QualityFactor
    from src.core.historical_news_fetcher import get_historical_news_fetcher
    logger.info("✅ Contextual modules imported")
except Exception as e:
    logger.error(f"❌ Failed to import contextual modules: {e}")
    sys.exit(1)

def calculate_momentum(prices, period=20):
    """Calculate momentum over period"""
    if len(prices) < period:
        return 0
    return (prices[-1] - prices[-period]) / prices[-period]

def calculate_simple_adx(prices, period=14):
    """Simple ADX approximation"""
    if len(prices) < period + 1:
        return 0
    
    # Calculate directional movement
    up_moves = []
    down_moves = []
    for i in range(len(prices) - period, len(prices)):
        if i > 0:
            change = prices[i] - prices[i-1]
            up_moves.append(max(change, 0))
            down_moves.append(max(-change, 0))
    
    avg_up = sum(up_moves) / len(up_moves) if up_moves else 0
    avg_down = sum(down_moves) / len(down_moves) if down_moves else 0
    
    if avg_up + avg_down == 0:
        return 0
    
    return abs(avg_up - avg_down) / (avg_up + avg_down) * 100

def prepare_multi_timeframe_data(client, instrument):
    """Prepare multi-timeframe data for price context analysis"""
    timeframes = {
        'M5': {'count': 200, 'granularity': 'M5'},
        'M15': {'count': 100, 'granularity': 'M15'},
        'H1': {'count': 48, 'granularity': 'H1'},
        'H4': {'count': 24, 'granularity': 'H4'},
        'D': {'count': 20, 'granularity': 'D'}  # Changed from D1 to D for OANDA compatibility
    }
    
    price_data = {}
    
    for tf, params in timeframes.items():
        try:
            # Fix for OANDA API - don't specify price type
            result = client.get_candles(
                instrument, 
                granularity=params['granularity'], 
                count=params['count']
            )
            
            if not result or 'candles' not in result:
                logger.warning(f"⚠️ No {tf} data for {instrument}")
                continue
            
            # Convert to DataFrame - handle both bid/ask and mid formats
            candles_data = []
            for c in result['candles']:
                if 'mid' in c:
                    # Mid price format
                    candle_data = {
                        'open': float(c['mid']['o']),
                        'high': float(c['mid']['h']),
                        'low': float(c['mid']['l']),
                        'close': float(c['mid']['c']),
                        'volume': float(c.get('volume', 0))
                    }
                else:
                    # Bid/ask format - use bid for consistency
                    candle_data = {
                        'open': float(c['bid']['o']),
                        'high': float(c['bid']['h']),
                        'low': float(c['bid']['l']),
                        'close': float(c['bid']['c']),
                        'volume': float(c.get('volume', 0))
                    }
                candles_data.append(candle_data)
            
            df = pd.DataFrame(candles_data)
            
            price_data[tf] = df
            logger.info(f"✅ {tf} data loaded for {instrument}: {len(df)} candles")
            
        except Exception as e:
            logger.error(f"❌ Error loading {tf} data for {instrument}: {e}")
    
    return price_data

def get_news_context(instrument):
    """Get news context for an instrument"""
    news_fetcher = get_historical_news_fetcher()
    now = datetime.now(pytz.UTC)
    
    # Get instrument-specific news context
    news_context = news_fetcher.get_instrument_news(
        instrument, 
        now,
        lookback_hours=4,
        lookahead_hours=4
    )
    
    return news_context

def scan_for_opportunities():
    """Scan market and find top opportunities using contextual analysis"""
    
    # Initialize contextual modules
    session_manager = get_session_manager()
    price_analyzer = get_price_context_analyzer()
    quality_scorer = get_quality_scoring()
    
    # Initialize OANDA client
    client = OandaClient(
        os.environ['OANDA_API_KEY'],
        os.environ['OANDA_ACCOUNT_ID'],
        'practice'
    )
    
    # Get account balance for position sizing
    account_info = client.get_account_info()
    balance = account_info.balance
    risk_per_trade = 0.01  # 1% risk per trade
    
    instruments = ['XAU_USD', 'EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'NZD_USD']
    opportunities = []
    
    # Get current session quality
    now = datetime.now(pytz.UTC)
    session_quality, active_sessions = session_manager.get_session_quality(now)
    session_description = session_manager.get_session_description(now)
    
    logger.info("\n" + "="*70)
    logger.info(f"MORNING MARKET SCAN - {datetime.now(pytz.timezone('Europe/London')).strftime('%A, %B %d, %Y %H:%M London')}")
    logger.info(f"Session: {session_description} (Quality: {session_quality}/100)")
    logger.info("="*70 + "\n")
    
    for instrument in instruments:
        logger.info(f"Analyzing {instrument}...")
        
        # Get multi-timeframe data
        price_data = prepare_multi_timeframe_data(client, instrument)
        if not price_data or 'M5' not in price_data:
            logger.warning(f"⚠️ Insufficient data for {instrument}")
            continue
        
        # Get current price
        current_price = price_data['M5']['close'].iloc[-1]
        
        # Get news context
        news_context = get_news_context(instrument)
        
        # Analyze price context
        try:
            contexts = price_analyzer.analyze_price_context(instrument, price_data)
            trade_context = price_analyzer.get_trade_context(instrument, current_price, contexts)
            
            logger.info(f"✅ Price context analyzed for {instrument}")
            logger.info(f"   Overall trend: {trade_context.get('overall_trend', 'unknown')}")
            
            # Check for high impact news
            if news_context.get('high_impact_upcoming', False):
                logger.warning(f"⚠️ High impact news upcoming for {instrument} - skipping")
                continue
            
            # Calculate basic indicators from M5 data
            m5_prices = price_data['M5']['close'].values
            
            # Calculate indicators
            momentum_1h = calculate_momentum(m5_prices, 12)  # 12 M5 bars = 1 hour
            momentum_4h = calculate_momentum(m5_prices, 48)  # 4 hours
            momentum_daily = calculate_momentum(m5_prices, 96) if len(m5_prices) >= 96 else 0  # ~8 hours
            adx = calculate_simple_adx(m5_prices, 14)
            
            # Determine direction based on multi-timeframe context
            overall_trend = trade_context.get('overall_trend', 'neutral')
            
            if overall_trend == 'bullish' and momentum_1h > 0.0005:
                direction = "BUY"
                strength = momentum_1h + 0.5  # Boost strength for trend alignment
            elif overall_trend == 'bearish' and momentum_1h < -0.0005:
                direction = "SELL"
                strength = abs(momentum_1h) + 0.5  # Boost strength for trend alignment
            else:
                # Check if we have a counter-trend opportunity with strong momentum
                if momentum_1h > 0.002 and momentum_4h > 0.001:
                    direction = "BUY"
                    strength = momentum_1h
                    logger.info(f"   Counter-trend BUY with strong momentum")
                elif momentum_1h < -0.002 and momentum_4h < -0.001:
                    direction = "SELL"
                    strength = abs(momentum_1h)
                    logger.info(f"   Counter-trend SELL with strong momentum")
                else:
                    logger.info(f"   ⏸️ No clear direction\n")
                    continue
            
            # Calculate stop loss and take profit based on key levels
            nearest_support = trade_context.get('nearest_support')
            nearest_resistance = trade_context.get('nearest_resistance')
            
            # Calculate ATR for fallback
            recent_range = max(m5_prices[-20:]) - min(m5_prices[-20:])
            atr = recent_range / 20
            
            if direction == "BUY":
                entry = current_price
                
                # Use support level if available and reasonable
                if nearest_support and (entry - nearest_support) / entry < 0.02:  # Within 2%
                    stop_loss = nearest_support * 0.998  # Just below support
                else:
                    stop_loss = entry - (atr * 2.5)
                
                # Use resistance level if available and reasonable
                if nearest_resistance and (nearest_resistance - entry) / entry < 0.05:  # Within 5%
                    take_profit = nearest_resistance * 0.998  # Just below resistance
                else:
                    take_profit = entry + (atr * 10)
            else:
                entry = current_price
                
                # Use resistance level if available and reasonable
                if nearest_resistance and (nearest_resistance - entry) / entry < 0.02:  # Within 2%
                    stop_loss = nearest_resistance * 1.002  # Just above resistance
                else:
                    stop_loss = entry + (atr * 2.5)
                
                # Use support level if available and reasonable
                if nearest_support and (entry - nearest_support) / entry < 0.05:  # Within 5%
                    take_profit = nearest_support * 1.002  # Just above support
                else:
                    take_profit = entry - (atr * 10)
            
            risk = abs(entry - stop_loss)
            reward = abs(take_profit - entry)
            rr_ratio = reward / risk if risk > 0 else 0
            
            # Create minimal data for quality scoring
            minimal_data = {
                "adx": adx,
                "momentum": momentum_1h,
                "volume": 1.0  # Default value, could be improved
            }
            
            # Combined context for quality scoring
            combined_context = {
                "timestamp": now,
                "session_quality": session_quality,
                "news": news_context,
                "price_context": trade_context,
                "timeframes": {
                    tf: {"trend": context.trend} for tf, context in contexts.items()
                }
            }
            
            # Score the trade using quality scoring module
            quality_result = quality_scorer.score_trade_quality(
                instrument, direction, minimal_data, combined_context)
            
            quality_score = quality_result.total_score
            
            # Only consider trades with quality > 60
            if quality_score < 60:
                logger.info(f"   ⏸️ Quality too low: {quality_score}/100\n")
                continue
            
            # Calculate position size
            sl_distance = abs(entry - stop_loss)
            dollar_risk = balance * risk_per_trade
            
            # For Gold (XAU_USD): 1 unit = 1 troy ounce
            # For Forex: 1 unit = 1 unit of base currency
            if instrument == 'XAU_USD':
                units = int(dollar_risk / sl_distance)
            else:
                # Forex pairs: risk in pips, need to adjust
                # Assuming 0.0001 pip value for most pairs, 0.01 for JPY pairs
                pip_value = 10 if 'JPY' in instrument else 10000
                units = int((dollar_risk / sl_distance) * pip_value)
            
            profit_if_win = units * abs(entry - take_profit)
            loss_if_lose = units * sl_distance
            
            # Add detailed quality factors
            quality_factors = {}
            for factor, score in quality_result.factors.items():
                quality_factors[factor.name] = score
            
            opportunities.append({
                'instrument': instrument,
                'direction': direction,
                'entry': entry,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'momentum_1h': momentum_1h * 100,  # as percentage
                'momentum_4h': momentum_4h * 100,
                'adx': adx,
                'quality': quality_score,
                'quality_factors': quality_factors,
                'recommendation': quality_result.recommendation,
                'explanation': quality_result.explanation,
                'rr_ratio': rr_ratio,
                'units': units,
                'dollar_risk': loss_if_lose,
                'dollar_reward': profit_if_win,
                'overall_trend': overall_trend,
                'nearest_support': nearest_support,
                'nearest_resistance': nearest_resistance,
                'session_quality': session_quality,
                'news_sentiment': news_context.get('sentiment', 0),
                'high_impact_news': news_context.get('high_impact_count', 0)
            })
            
            logger.info(f"   ✅ {direction} Setup - Quality: {quality_score}/100")
            logger.info(f"      Entry: {entry:.5f}")
            logger.info(f"      SL: {stop_loss:.5f} | TP: {take_profit:.5f}")
            logger.info(f"      R:R = 1:{rr_ratio:.1f}")
            logger.info(f"      Recommendation: {quality_result.recommendation}")
            logger.info(f"      {quality_result.explanation}\n")
            
        except Exception as e:
            logger.error(f"❌ Error analyzing {instrument}: {e}")
            continue
    
    # Rank by quality
    opportunities.sort(key=lambda x: x['quality'], reverse=True)
    
    return opportunities

def send_opportunities_to_telegram(opportunities):
    """Send top opportunities to Telegram with enhanced contextual information"""
    
    notifier = TelegramNotifier()
    session_manager = get_session_manager()
    
    # Get current session info
    now = datetime.now(pytz.UTC)
    session_quality, active_sessions = session_manager.get_session_quality(now)
    session_description = session_manager.get_session_description(now)
    
    # Get next prime session
    _, next_prime_message = session_manager.get_next_prime_session()
    
    if not opportunities:
        message = f"""🔍 **MORNING MARKET SCAN - {datetime.now(pytz.timezone('Europe/London')).strftime('%A %H:%M')}**

❌ No quality setups found right now.

**Session Status:**
{session_description} (Quality: {session_quality}/100)

**Market Status:**
All pairs checked - no clear momentum or trend strength meeting quality threshold (60/100).

**Recommendation:** 
Wait for clearer setups. Will scan again at 1:00 PM (NY overlap).

{next_prime_message}"""
        
        notifier.send_system_status('Morning Scan - No Setups', message)
        return
    
    # Build message with top 5 opportunities and contextual information
    message = f"""🎯 **ENHANCED MORNING SCAN - {datetime.now(pytz.timezone('Europe/London')).strftime('%A %H:%M London')}**

**Session:** {session_description} (Quality: {session_quality}/100)

Found {len(opportunities)} quality setups:\n\n"""
    
    for i, opp in enumerate(opportunities[:5], 1):
        # Format quality factors for display
        quality_factors = []
        for factor, score in opp.get('quality_factors', {}).items():
            if score >= 70:
                emoji = "🔥"  # Fire for high scores
            elif score >= 50:
                emoji = "✅"  # Check for good scores
            else:
                emoji = "⚠️"  # Warning for lower scores
            
            quality_factors.append(f"{emoji} {factor}: {score}")
        
        # Format quality factors as string
        quality_factors_str = "\n".join(quality_factors[:5])  # Show top 5 factors
        
        # Add news context if available
        news_info = ""
        if opp.get('news_sentiment') is not None:
            sentiment = opp['news_sentiment']
            if sentiment > 0.3:
                news_info = "📰 News: Positive sentiment"
            elif sentiment < -0.3:
                news_info = "📰 News: Negative sentiment"
            else:
                news_info = "📰 News: Neutral"
        
        # Add key levels info
        levels_info = ""
        if opp.get('nearest_support') and opp.get('nearest_resistance'):
            levels_info = f"🔍 Key Levels: S: {opp.get('nearest_support', 0):.5f} | R: {opp.get('nearest_resistance', 0):.5f}"
        
        # Add trend alignment info
        trend_info = f"📈 Overall Trend: {opp.get('overall_trend', 'unknown').capitalize()}"
        
        message += f"""**#{i} - {opp['instrument']} {opp['direction']}** (Quality: {opp['quality']}/100)
📍 Entry: {opp['entry']:.5f}
🛑 Stop Loss: {opp['stop_loss']:.5f}
🎯 Take Profit: {opp['take_profit']:.5f}
📊 R:R Ratio: 1:{opp['rr_ratio']:.1f}
💰 Position: {opp['units']:,} units
💵 Risk: ${opp['dollar_risk']:,.2f} | Reward: ${opp['dollar_reward']:,.2f}
{trend_info}
{levels_info}
{news_info}

**Quality Analysis:**
{opp.get('explanation', 'No explanation available')}

"""
    
    message += f"""**How to Execute:**
1. Check these setups on your chart and verify the context
2. Confirm trend alignment on multiple timeframes
3. Enter at current price or wait for pullback to key level
4. Set SL and TP as shown above
5. Consider trailing stops after +1.5% profit

**Next Scan:** 1:00 PM (London/NY overlap) 📊"""
    
    notifier.send_system_status(f'{len(opportunities)} Quality Setups Found', message)
    logger.info(f"\n✅ Sent {len(opportunities)} opportunities to Telegram!")

def main():
    """Main scanner with enhanced contextual analysis"""
    try:
        logger.info("🔍 Starting enhanced morning scanner with contextual analysis...")
        opportunities = scan_for_opportunities()
        
        logger.info("\n" + "="*70)
        logger.info(f"SCAN COMPLETE: {len(opportunities)} quality opportunities found")
        logger.info("="*70 + "\n")
        
        send_opportunities_to_telegram(opportunities)
        
        # Save opportunities to file for reference
        import json
        with open('latest_opportunities.json', 'w') as f:
            json.dump(opportunities, f, indent=2, default=str)
        logger.info("✅ Opportunities saved to latest_opportunities.json")
        
        return opportunities
    except Exception as e:
        logger.error(f"❌ Error in main scanner: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        # Send error notification
        try:
            notifier = TelegramNotifier()
            notifier.send_system_status(
                'Scanner Error', 
                f"❌ Morning scanner encountered an error:\n\n{str(e)}\n\nCheck logs for details."
            )
        except:
            pass
        
        return []

if __name__ == '__main__':
    main()

