#!/usr/bin/env python3
from src.core.settings import settings
"""
USD/JPY Pattern Analysis - Last 3 Months
Analyzes weekly and intraday patterns, news correlations, and trading opportunities.
"""
import os
import sys
import requests
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict
import pytz

# OANDA Configuration
OANDA_API_KEY = settings.oanda_api_key
if not OANDA_API_KEY:
    raise ValueError("OANDA_API_KEY environment variable must be set")
OANDA_BASE_URL = os.getenv("OANDA_BASE_URL", "https://api-fxpractice.oanda.com")

# London timezone
LONDON_TZ = pytz.timezone("Europe/London")

def fetch_oanda_candles(instrument: str, granularity: str, from_time: datetime, to_time: datetime, account_id: str = None) -> List[Dict]:
    """Fetch candle data from OANDA API using count parameter (more reliable)."""
    url = f"{OANDA_BASE_URL}/v3/instruments/{instrument}/candles"
    headers = {
        "Authorization": f"Bearer {OANDA_API_KEY}",
        "Content-Type": "application/json"
    }
    
    all_candles = []
    
    # Calculate how many candles we need (approx 3 months = 90 days * 24 hours = 2160 for H1)
    # OANDA allows up to 5000 candles per request
    # Use count parameter working backwards from now
    print(f"Fetching {instrument} data (last 3 months = ~{2160} candles for H1)...")
    
    # Calculate approximate count needed
    if granularity == "H1":
        total_hours = (to_time - from_time).total_seconds() / 3600
        count_needed = int(total_hours)
    elif granularity == "M15":
        total_minutes = (to_time - from_time).total_seconds() / 60
        count_needed = int(total_minutes / 15)
    elif granularity == "M5":
        total_minutes = (to_time - from_time).total_seconds() / 60
        count_needed = int(total_minutes / 5)
    else:
        count_needed = 5000  # Default max
    
    # OANDA max is 5000, so we may need multiple requests
    max_per_request = 5000
    remaining = count_needed
    current_count = min(remaining, max_per_request)
    
    try:
        # First request: get the most recent candles
        params = {
            "granularity": granularity,
            "price": "M",  # Mid prices
            "count": current_count
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        if response.status_code != 200:
            print(f"Error fetching candles: {response.status_code} - {response.text[:200]}")
            return []
        
        data = response.json()
        candles = data.get("candles", [])
        
        if not candles:
            return []
        
        # Filter out incomplete candles and reverse to chronological order
        valid_candles = [c for c in candles if c.get("complete", False)]
        valid_candles.reverse()  # Oldest first
        
        # Filter to only include candles in our date range
        filtered_candles = []
        for candle in valid_candles:
            try:
                time_str = candle.get("time", "")
                if not time_str:
                    continue
                dt_utc = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
                if from_time <= dt_utc <= to_time:
                    filtered_candles.append(candle)
            except:
                continue
        
        all_candles.extend(filtered_candles)
        print(f"  Fetched {len(filtered_candles)} candles (from {len(valid_candles)} total)")
        
        if filtered_candles:
            first_time = datetime.fromisoformat(filtered_candles[0].get("time", "").replace("Z", "+00:00"))
            last_time = datetime.fromisoformat(filtered_candles[-1].get("time", "").replace("Z", "+00:00"))
            print(f"  Date range: {first_time.strftime('%Y-%m-%d %H:%M')} to {last_time.strftime('%Y-%m-%d %H:%M')}")
        
        # If we need more data and the first candle is newer than our from_time, fetch more
        if filtered_candles and len(filtered_candles) < count_needed * 0.9:
            oldest_time_str = filtered_candles[0].get("time", "")
            oldest_dt = datetime.fromisoformat(oldest_time_str.replace("Z", "+00:00"))
            
            if oldest_dt > from_time:
                print(f"  Need more historical data, fetching additional candles...")
                # Use from/to to get older data
                params2 = {
                    "from": from_time.strftime("%Y-%m-%dT%H:%M:%S.000000000Z"),
                    "to": oldest_dt.strftime("%Y-%m-%dT%H:%M:%S.000000000Z"),
                    "granularity": granularity,
                    "price": "M",
                    "count": 5000
                }
                response2 = requests.get(url, headers=headers, params=params2, timeout=30)
                if response2.status_code == 200:
                    data2 = response2.json()
                    additional_candles = [c for c in data2.get("candles", []) if c.get("complete", False)]
                    if additional_candles:
                        additional_candles.reverse()
                        all_candles = additional_candles + all_candles
                        print(f"  Added {len(additional_candles)} additional candles")
            
    except Exception as e:
        print(f"Exception fetching candles: {e}")
        import traceback
        traceback.print_exc()
    
    return all_candles


def candles_to_dataframe(candles: List[Dict]) -> pd.DataFrame:
    """Convert OANDA candles to pandas DataFrame."""
    data = []
    for candle in candles:
        time_str = candle.get("time", "")
        mid = candle.get("mid", {})
        
        if not mid or not time_str:
            continue
        
        try:
            # Parse time and convert to London time
            dt_utc = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
            dt_london = dt_utc.astimezone(LONDON_TZ)
            
            data.append({
                "time": dt_london,
                "time_utc": dt_utc,
                "open": float(mid.get("o", 0)),
                "high": float(mid.get("h", 0)),
                "low": float(mid.get("l", 0)),
                "close": float(mid.get("c", 0)),
                "volume": int(candle.get("volume", 0)),
                "complete": candle.get("complete", False)
            })
        except Exception as e:
            continue
    
    if not data:
        return pd.DataFrame()
    
    df = pd.DataFrame(data)
    df.set_index("time", inplace=True)
    df.sort_index(inplace=True)
    return df


def analyze_weekly_patterns(df: pd.DataFrame) -> Dict[str, Any]:
    """Analyze which day of week typically has high/low."""
    df = df.copy()
    df["day_of_week"] = df.index.day_name()
    df["week"] = df.index.to_period("W")
    
    results = {
        "weekly_highs": defaultdict(int),
        "weekly_lows": defaultdict(int),
        "day_stats": defaultdict(lambda: {"highs": 0, "lows": 0, "avg_range": [], "avg_change": []}),
        "high_of_week_days": [],
        "low_of_week_days": []
    }
    
    # Group by week
    for week, week_data in df.groupby("week"):
        if len(week_data) < 10:  # Skip incomplete weeks
            continue
        
        week_high = week_data["high"].max()
        week_low = week_data["low"].min()
        week_high_day = week_data[week_data["high"] == week_high]["day_of_week"].iloc[0]
        week_low_day = week_data[week_data["low"] == week_low]["day_of_week"].iloc[0]
        
        results["weekly_highs"][week_high_day] += 1
        results["weekly_lows"][week_low_day] += 1
        results["high_of_week_days"].append(week_high_day)
        results["low_of_week_days"].append(week_low_day)
        
        # Per-day statistics
        for day_name, day_data in week_data.groupby("day_of_week"):
            day_range = (day_data["high"].max() - day_data["low"].min()) / day_data["close"].mean() * 100
            day_change = (day_data["close"].iloc[-1] - day_data["open"].iloc[0]) / day_data["open"].iloc[0] * 100
            
            results["day_stats"][day_name]["avg_range"].append(day_range)
            results["day_stats"][day_name]["avg_change"].append(day_change)
            
            if day_name == week_high_day:
                results["day_stats"][day_name]["highs"] += 1
            if day_name == week_low_day:
                results["day_stats"][day_name]["lows"] += 1
    
    # Calculate averages
    for day_name in results["day_stats"]:
        stats = results["day_stats"][day_name]
        stats["avg_range_pct"] = np.mean(stats["avg_range"]) if stats["avg_range"] else 0
        stats["avg_change_pct"] = np.mean(stats["avg_change"]) if stats["avg_change"] else 0
        stats["high_frequency"] = stats["highs"] / max(sum(results["weekly_highs"].values()), 1) * 100
        stats["low_frequency"] = stats["lows"] / max(sum(results["weekly_lows"].values()), 1) * 100
    
    return results


def analyze_intraday_patterns(df: pd.DataFrame) -> Dict[str, Any]:
    """Analyze intraday time patterns."""
    df = df.copy()
    df["hour"] = df.index.hour
    df["minute"] = df.index.minute
    df["time_of_day"] = df["hour"] + df["minute"] / 60.0
    
    results = {
        "hourly_highs": defaultdict(list),
        "hourly_lows": defaultdict(list),
        "hourly_ranges": defaultdict(list),
        "hourly_volumes": defaultdict(list),
        "hourly_changes": defaultdict(list),
        "peak_hours": [],
        "quiet_hours": []
    }
    
    # Group by hour
    for hour in range(24):
        hour_data = df[df["hour"] == hour]
        if len(hour_data) == 0:
            continue
        
        results["hourly_highs"][hour] = hour_data["high"].values.tolist()
        results["hourly_lows"][hour] = hour_data["low"].values.tolist()
        results["hourly_ranges"][hour] = ((hour_data["high"] - hour_data["low"]) / hour_data["close"] * 100).values.tolist()
        results["hourly_volumes"][hour] = hour_data["volume"].values.tolist()
        
        # Calculate hour-over-hour change
        if len(hour_data) > 0:
            hour_start = hour_data["open"].iloc[0]
            hour_end = hour_data["close"].iloc[-1]
            hour_change = (hour_end - hour_start) / hour_start * 100
            results["hourly_changes"][hour].append(hour_change)
    
    # Calculate statistics per hour
    hourly_stats = {}
    for hour in range(24):
        if hour in results["hourly_ranges"] and results["hourly_ranges"][hour]:
            hourly_stats[hour] = {
                "avg_range_pct": np.mean(results["hourly_ranges"][hour]),
                "avg_volume": np.mean(results["hourly_volumes"][hour]) if results["hourly_volumes"][hour] else 0,
                "avg_change_pct": np.mean(results["hourly_changes"][hour]) if results["hourly_changes"][hour] else 0,
                "max_range_pct": np.max(results["hourly_ranges"][hour]),
                "min_range_pct": np.min(results["hourly_ranges"][hour])
            }
    
    # Identify peak and quiet hours
    if hourly_stats:
        avg_ranges = [(h, stats["avg_range_pct"]) for h, stats in hourly_stats.items()]
        avg_ranges.sort(key=lambda x: x[1], reverse=True)
        results["peak_hours"] = [h for h, _ in avg_ranges[:5]]
        results["quiet_hours"] = [h for h, _ in avg_ranges[-5:]]
    
    results["hourly_stats"] = hourly_stats
    return results


def fetch_economic_calendar(start_date: datetime, end_date: datetime) -> List[Dict]:
    """Fetch economic calendar events from Finnhub."""
    finnhub_key = os.getenv("FINNHUB_KEY", "")
    
    if not finnhub_key:
        try:
            import subprocess
            result = subprocess.run(
                ["gcloud", "secrets", "versions", "access", "latest", "--secret=finnhub-key", "--project=ai-quant-trading"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                finnhub_key = result.stdout.strip()
        except:
            pass
    
    if not finnhub_key:
        return []
    
    url = "https://finnhub.io/api/v1/calendar/economic"
    events = []
    
    print(f"  Fetching economic calendar from Finnhub...")
    
    # Fetch in monthly chunks
    current_date = start_date
    while current_date < end_date:
        month_end = min(current_date + timedelta(days=31), end_date)
        
        params = {
            "from": current_date.strftime("%Y-%m-%d"),
            "to": month_end.strftime("%Y-%m-%d"),
            "token": finnhub_key
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                calendar_events = data.get("economicCalendar", [])
                
                # Filter for USD/JPY relevant events (US, Japan, or major central banks)
                relevant_events = []
                for event in calendar_events:
                    country = event.get("country", "").upper()
                    # Include US, Japan, and major economic events
                    if any(c in country for c in ["US", "JP", "JPY", "USD"]) or event.get("impact", "") == "high":
                        relevant_events.append({
                            "time": event.get("time", ""),
                            "country": country,
                            "event": event.get("event", ""),
                            "impact": event.get("impact", ""),
                            "forecast": event.get("forecast"),
                            "actual": event.get("actual"),
                            "type": "economic_calendar"
                        })
                
                events.extend(relevant_events)
                print(f"    Fetched {len(relevant_events)} relevant events from {current_date.strftime('%Y-%m-%d')} to {month_end.strftime('%Y-%m-%d')}")
                
            elif response.status_code == 429:
                print(f"    Finnhub rate limit reached")
                break
            else:
                print(f"    Error fetching calendar: {response.status_code}")
            
            current_date = month_end
            import time
            time.sleep(1)  # Rate limiting
            
        except Exception as e:
            print(f"    Exception fetching calendar: {e}")
            break
    
    return events


def fetch_news_events(start_date: datetime, end_date: datetime) -> List[Dict]:
    """Fetch news events from Marketaux API if available."""
    # Try to get from environment or Google Cloud secrets
    marketaux_keys_str = os.getenv("MARKETAUX_KEY", "") or os.getenv("MARKETAUX_KEYS", "")
    
    # If not in env, try fetching from GCloud secrets (if gcloud is available)
    if not marketaux_keys_str:
        try:
            import subprocess
            result = subprocess.run(
                ["gcloud", "secrets", "versions", "access", "latest", "--secret=marketaux-api-key", "--project=ai-quant-trading"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                marketaux_keys_str = result.stdout.strip()
        except:
            pass
    
    if not marketaux_keys_str:
        return []
    
    # Parse comma-separated keys
    marketaux_keys = [k.strip() for k in marketaux_keys_str.split(",") if k.strip()]
    if not marketaux_keys:
        return []
    
    # Use first key for now
    marketaux_key = marketaux_keys[0]
    
    url = "https://api.marketaux.com/v1/news/all"
    
    news_events = []
    current_date = start_date
    
    print(f"\nFetching news events...")
    
    while current_date < end_date:
        params = {
            "api_token": marketaux_key,
            "symbols": "USD,JPY,USDJPY",
            "published_after": current_date.strftime("%Y-%m-%d"),
            "published_before": min(current_date + timedelta(days=30), end_date).strftime("%Y-%m-%d"),
            "page_size": 100,
            "limit": 100
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                articles = data.get("data", [])
                news_events.extend(articles)
                print(f"  Fetched {len(articles)} news articles")
            elif response.status_code == 402:
                print(f"  Marketaux API limit reached")
                break
            else:
                print(f"  Error fetching news: {response.status_code}")
            
            current_date += timedelta(days=30)
            import time
            time.sleep(1)  # Rate limiting
            
        except Exception as e:
            print(f"  Exception fetching news: {e}")
            break
    
    return news_events


def correlate_news_with_price(news_events: List[Dict], df: pd.DataFrame) -> Dict[str, Any]:
    """Correlate news events with price movements."""
    if not news_events or df.empty:
        return {"correlations": [], "high_impact_movements": []}
    
    correlations = []
    high_impact_movements = []
    
    for news in news_events:
        try:
            # Handle different time formats (news vs calendar)
            published_str = news.get("published_at") or news.get("time", "")
            if not published_str:
                continue
            
            # Parse news time (handle different formats)
            if "T" in published_str:
                # ISO format with time
                dt_utc = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
            else:
                # Date only format from Finnhub
                dt_utc = datetime.strptime(published_str[:10], "%Y-%m-%d")
                dt_utc = LONDON_TZ.localize(dt_utc.replace(hour=12, minute=0)).astimezone(pytz.UTC)
            
            dt_london = dt_utc.astimezone(LONDON_TZ)
            
            # Find price data around news time (±3 hours for economic calendar, ±2 for news)
            window_hours = 3 if news.get("type") == "economic_calendar" else 2
            window_start = dt_london - timedelta(hours=window_hours)
            window_end = dt_london + timedelta(hours=window_hours)
            
            price_window = df[(df.index >= window_start) & (df.index <= window_end)]
            
            if len(price_window) < 2:
                continue
            
            pre_news_price = price_window.iloc[0]["close"]
            post_news_price = price_window.iloc[-1]["close"]
            price_change = (post_news_price - pre_news_price) / pre_news_price * 100
            max_range = (price_window["high"].max() - price_window["low"].min()) / pre_news_price * 100
            
            sentiment = news.get("sentiment", "")
            relevance = news.get("relevance_score", 0)
            impact = news.get("impact", "")
            
            # Get title/event name
            title = news.get("title", "")[:100] or news.get("event", "")[:100]
            
            correlation = {
                "news_time": dt_london,
                "title": title,
                "sentiment": sentiment,
                "impact": impact,
                "relevance": relevance,
                "price_change_pct": price_change,
                "max_range_pct": max_range,
                "pre_price": pre_news_price,
                "post_price": post_news_price,
                "country": news.get("country", ""),
                "type": news.get("type", "news")
            }
            
            correlations.append(correlation)
            
            # Flag high-impact movements
            if abs(price_change) > 0.1 or max_range > 0.15 or impact == "high":
                high_impact_movements.append(correlation)
        
        except Exception as e:
            continue
    
    return {
        "correlations": correlations,
        "high_impact_movements": high_impact_movements
    }


def generate_report(weekly_analysis: Dict, intraday_analysis: Dict, news_correlation: Dict, df: pd.DataFrame) -> str:
    """Generate comprehensive analysis report."""
    report = []
    report.append("=" * 80)
    report.append("USD/JPY PATTERN ANALYSIS - LAST 3 MONTHS")
    report.append("=" * 80)
    report.append(f"Analysis Date: {datetime.now(LONDON_TZ).strftime('%Y-%m-%d %H:%M:%S %Z')}")
    report.append(f"Data Range: {df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')}")
    report.append(f"Total Candles: {len(df)}")
    report.append("")
    
    # Weekly patterns
    report.append("─" * 80)
    report.append("WEEKLY PATTERNS")
    report.append("─" * 80)
    report.append("")
    
    report.append("Days that Create WEEKLY HIGHS (frequency):")
    weekly_highs = weekly_analysis["weekly_highs"]
    total_weeks = sum(weekly_highs.values())
    for day, count in sorted(weekly_highs.items(), key=lambda x: x[1], reverse=True):
        pct = (count / total_weeks * 100) if total_weeks > 0 else 0
        report.append(f"  {day:12s}: {count:3d} times ({pct:5.1f}%)")
    
    report.append("")
    report.append("Days that Create WEEKLY LOWS (frequency):")
    weekly_lows = weekly_analysis["weekly_lows"]
    total_weeks = sum(weekly_lows.values())
    for day, count in sorted(weekly_lows.items(), key=lambda x: x[1], reverse=True):
        pct = (count / total_weeks * 100) if total_weeks > 0 else 0
        report.append(f"  {day:12s}: {count:3d} times ({pct:5.1f}%)")
    
    report.append("")
    report.append("Per-Day Statistics (Average):")
    report.append(f"{'Day':<12} {'Avg Range %':<12} {'Avg Change %':<12} {'High Freq %':<12} {'Low Freq %':<12}")
    report.append("-" * 60)
    
    days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    for day in days_order:
        if day in weekly_analysis["day_stats"]:
            stats = weekly_analysis["day_stats"][day]
            report.append(
                f"{day:<12} {stats['avg_range_pct']:>10.3f}% {stats['avg_change_pct']:>10.3f}% "
                f"{stats['high_frequency']:>10.1f}% {stats['low_frequency']:>10.1f}%"
            )
    
    # Intraday patterns
    report.append("")
    report.append("─" * 80)
    report.append("INTRADAY PATTERNS (London Time)")
    report.append("─" * 80)
    report.append("")
    
    report.append("TOP 5 MOST VOLATILE HOURS (Peak Trading Hours):")
    peak_hours = intraday_analysis["peak_hours"]
    for i, hour in enumerate(peak_hours[:5], 1):
        stats = intraday_analysis["hourly_stats"].get(hour, {})
        report.append(
            f"  {i}. {hour:02d}:00 - Avg Range: {stats.get('avg_range_pct', 0):.3f}%, "
            f"Avg Change: {stats.get('avg_change_pct', 0):.3f}%, "
            f"Avg Volume: {stats.get('avg_volume', 0):.0f}"
        )
    
    report.append("")
    report.append("TOP 5 QUIETEST HOURS:")
    quiet_hours = intraday_analysis["quiet_hours"]
    for i, hour in enumerate(quiet_hours[:5], 1):
        stats = intraday_analysis["hourly_stats"].get(hour, {})
        report.append(
            f"  {i}. {hour:02d}:00 - Avg Range: {stats.get('avg_range_pct', 0):.3f}%, "
            f"Avg Change: {stats.get('avg_change_pct', 0):.3f}%"
        )
    
    report.append("")
    report.append("Hourly Breakdown (London Time):")
    report.append(f"{'Hour':<6} {'Avg Range %':<12} {'Avg Change %':<12} {'Avg Volume':<12} {'Max Range %':<12}")
    report.append("-" * 60)
    
    for hour in range(24):
        if hour in intraday_analysis["hourly_stats"]:
            stats = intraday_analysis["hourly_stats"][hour]
            report.append(
                f"{hour:02d}:00  {stats['avg_range_pct']:>10.3f}% {stats['avg_change_pct']:>10.3f}% "
                f"{stats['avg_volume']:>10.0f}  {stats['max_range_pct']:>10.3f}%"
            )
    
    # News correlations
    if news_correlation.get("correlations"):
        report.append("")
        report.append("─" * 80)
        report.append("NEWS EVENT CORRELATIONS")
        report.append("─" * 80)
        report.append("")
        
        high_impact = news_correlation["high_impact_movements"]
        if high_impact:
            report.append(f"HIGH-IMPACT NEWS/CALENDAR MOVEMENTS ({len(high_impact)} events):")
            report.append("")
            for i, event in enumerate(sorted(high_impact, key=lambda x: abs(x["price_change_pct"]), reverse=True)[:15], 1):
                event_type = event.get("type", "news").replace("_", " ").title()
                title = event.get("title", "N/A")[:60]
                country = event.get("country", "")
                impact = event.get("impact", "")
                
                report.append(f"{i}. {event['news_time'].strftime('%Y-%m-%d %H:%M')} ({event_type}) - {title}")
                if country:
                    report.append(f"   Country: {country}", end="")
                if impact:
                    report.append(f" | Impact: {impact}", end="")
                if event.get("sentiment"):
                    report.append(f" | Sentiment: {event['sentiment']}", end="")
                report.append("")
                report.append(
                    f"   Price Change: {event['price_change_pct']:+.3f}%, "
                    f"Range: {event['max_range_pct']:.3f}%"
                )
                report.append("")
        
        # Sentiment analysis
        positive_news = [e for e in news_correlation["correlations"] if e.get("sentiment") == "positive"]
        negative_news = [e for e in news_correlation["correlations"] if e.get("sentiment") == "negative"]
        neutral_news = [e for e in news_correlation["correlations"] if e.get("sentiment") == "neutral"]
        
        if positive_news or negative_news:
            report.append("Sentiment-Based Price Movements:")
            if positive_news:
                avg_pos_change = np.mean([e["price_change_pct"] for e in positive_news])
                report.append(f"  Positive News ({len(positive_news)} events): Avg Price Change = {avg_pos_change:+.3f}%")
            if negative_news:
                avg_neg_change = np.mean([e["price_change_pct"] for e in negative_news])
                report.append(f"  Negative News ({len(negative_news)} events): Avg Price Change = {avg_neg_change:+.3f}%")
            if neutral_news:
                avg_neu_change = np.mean([e["price_change_pct"] for e in neutral_news])
                report.append(f"  Neutral News ({len(neutral_news)} events): Avg Price Change = {avg_neu_change:+.3f}%")
    
    # Trading insights
    report.append("")
    report.append("─" * 80)
    report.append("TRADING INSIGHTS & RECOMMENDATIONS")
    report.append("─" * 80)
    report.append("")
    
    # Best day for high/low
    best_high_day = max(weekly_analysis["weekly_highs"].items(), key=lambda x: x[1])[0] if weekly_analysis["weekly_highs"] else "N/A"
    best_low_day = max(weekly_analysis["weekly_lows"].items(), key=lambda x: x[1])[0] if weekly_analysis["weekly_lows"] else "N/A"
    
    report.append(f"✓ Best day to EXPECT WEEKLY HIGH: {best_high_day}")
    report.append(f"✓ Best day to EXPECT WEEKLY LOW: {best_low_day}")
    
    if peak_hours:
        report.append(f"✓ BEST TRADING HOURS (London Time): {', '.join([f'{h:02d}:00' for h in peak_hours[:3]])}")
    if quiet_hours:
        report.append(f"✓ QUIETEST HOURS (avoid trading): {', '.join([f'{h:02d}:00' for h in quiet_hours[:3]])}")
    
    # Additional patterns
    report.append("")
    report.append("Additional Patterns:")
    
    # Check for Monday/Friday effects
    monday_stats = weekly_analysis["day_stats"].get("Monday", {})
    friday_stats = weekly_analysis["day_stats"].get("Friday", {})
    
    if monday_stats.get("avg_change_pct", 0) > 0.05:
        report.append("  • Monday tends to show positive momentum")
    elif monday_stats.get("avg_change_pct", 0) < -0.05:
        report.append("  • Monday tends to show negative momentum")
    
    if friday_stats.get("avg_range_pct", 0) > weekly_analysis["day_stats"].get("Tuesday", {}).get("avg_range_pct", 0):
        report.append("  • Friday shows higher volatility than average")
    
    report.append("")
    report.append("=" * 80)
    
    return "\n".join(report)


def main():
    """Main analysis function."""
    print("USD/JPY Pattern Analysis - Last 3 Months")
    print("=" * 80)
    print()
    
    # Calculate date range (3 months ago to now)
    end_date = datetime.now(LONDON_TZ)
    start_date = end_date - timedelta(days=90)
    
    # Fetch historical data (use H1 candles for good granularity)
    print("Step 1: Fetching historical price data...")
    candles = fetch_oanda_candles("USD_JPY", "H1", start_date, end_date)
    
    if not candles:
        print("ERROR: No candle data retrieved. Check API key and network connection.")
        return
    
    # Convert to DataFrame
    print("\nStep 2: Processing data...")
    df = candles_to_dataframe(candles)
    
    if df.empty:
        print("ERROR: DataFrame is empty after processing.")
        return
    
    print(f"Processed {len(df)} candles")
    print(f"Date range: {df.index[0]} to {df.index[-1]}")
    
    # Analyze weekly patterns
    print("\nStep 3: Analyzing weekly patterns...")
    weekly_analysis = analyze_weekly_patterns(df)
    
    # Analyze intraday patterns
    print("Step 4: Analyzing intraday patterns...")
    intraday_analysis = analyze_intraday_patterns(df)
    
    # Fetch and correlate news
    print("Step 5: Fetching news events...")
    # Set Marketaux key from GCloud secrets for this run
    if not (settings.marketaux_keys[0] if settings.marketaux_keys else None) and not (",".join(settings.marketaux_keys) if settings.marketaux_keys else None):
        try:
            import subprocess
            result = subprocess.run(
                ["gcloud", "secrets", "versions", "access", "latest", "--secret=marketaux-api-key", "--project=ai-quant-trading"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                marketaux_keys_str = result.stdout.strip()
                # Use first key for environment
                if marketaux_keys_str:
                    keys_list = [k.strip() for k in marketaux_keys_str.split(",") if k.strip()]
                    if keys_list:
                        os.environ["MARKETAUX_KEY"] = keys_list[0]
                        print(f"  Loaded Marketaux API key from Google Cloud secrets")
        except Exception as e:
            print(f"  Note: Could not fetch from GCloud secrets: {e}")
    
    # Fetch news and economic calendar
    news_events = fetch_news_events(start_date, end_date)
    calendar_events = fetch_economic_calendar(start_date, end_date)
    
    # Combine all events
    all_events = news_events + calendar_events
    
    news_correlation = {"correlations": [], "high_impact_movements": []}
    
    if all_events:
        print(f"Correlating {len(all_events)} total events ({len(news_events)} news, {len(calendar_events)} calendar) with price movements...")
        news_correlation = correlate_news_with_price(all_events, df)
    else:
        print("  No news/calendar events fetched (API keys may not be configured or limits reached)")
    
    # Generate report
    print("\nStep 6: Generating report...")
    report = generate_report(weekly_analysis, intraday_analysis, news_correlation, df)
    
    # Save report
    output_file = f"usd_jpy_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(report)
    
    print(f"\n{'='*80}")
    print(f"Analysis complete! Report saved to: {output_file}")
    print(f"{'='*80}\n")
    
    # Print summary to console
    print(report)
    
    # Save data for further analysis
    df.to_csv(f"usd_jpy_data_{datetime.now().strftime('%Y%m%d')}.csv")


if __name__ == "__main__":
    main()

