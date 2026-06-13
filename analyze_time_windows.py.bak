#!/usr/bin/env python3
"""
Deep Dive Time Window Analysis - USD/JPY
Analyzes specific time windows for trading opportunities:
- Monday mornings (weekly low probability: 35.7%)
- Friday afternoons (weekly high probability: 28.6%)
- Prime trading hours (13:00-15:00 London)
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
OANDA_API_KEY = os.getenv("OANDA_API_KEY")
if not OANDA_API_KEY:
    raise ValueError("OANDA_API_KEY environment variable must be set")
OANDA_BASE_URL = os.getenv("OANDA_BASE_URL", "https://api-fxpractice.oanda.com")

# London timezone
LONDON_TZ = pytz.timezone("Europe/London")


def fetch_oanda_candles(instrument: str, granularity: str, from_time: datetime, to_time: datetime) -> List[Dict]:
    """Fetch candle data from OANDA API using count parameter."""
    url = f"{OANDA_BASE_URL}/v3/instruments/{instrument}/candles"
    headers = {
        "Authorization": f"Bearer {OANDA_API_KEY}",
        "Content-Type": "application/json"
    }
    
    all_candles = []
    
    if granularity == "H1":
        total_hours = (to_time - from_time).total_seconds() / 3600
        count_needed = int(total_hours)
    else:
        count_needed = 5000
    
    max_per_request = 5000
    current_count = min(count_needed, max_per_request)
    
    try:
        params = {
            "granularity": granularity,
            "price": "M",
            "count": current_count
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        if response.status_code != 200:
            return []
        
        data = response.json()
        candles = data.get("candles", [])
        
        if not candles:
            return []
        
        valid_candles = [c for c in candles if c.get("complete", False)]
        valid_candles.reverse()
        
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
        
        if filtered_candles and len(filtered_candles) < count_needed * 0.9:
            oldest_time_str = filtered_candles[0].get("time", "")
            oldest_dt = datetime.fromisoformat(oldest_time_str.replace("Z", "+00:00"))
            
            if oldest_dt > from_time:
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
            
    except Exception as e:
        print(f"Exception fetching candles: {e}")
    
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
        except Exception:
            continue
    
    if not data:
        return pd.DataFrame()
    
    df = pd.DataFrame(data)
    df.set_index("time", inplace=True)
    df.sort_index(inplace=True)
    return df


def analyze_monday_mornings(df: pd.DataFrame) -> Dict[str, Any]:
    """Deep dive into Monday morning patterns."""
    df = df.copy()
    df["day_of_week"] = df.index.day_name()
    df["hour"] = df.index.hour
    df["date"] = df.index.date
    
    results = {
        "monday_lows": [],
        "monday_morning_behavior": defaultdict(list),
        "after_monday_low": [],
        "monday_vs_week_high": [],
        "hourly_breakdown": defaultdict(lambda: {"lows": 0, "highs": 0, "ranges": [], "changes": []})
    }
    
    # Group by week
    df["week"] = df.index.to_period("W")
    
    for week, week_data in df.groupby("week"):
        if len(week_data) < 10:
            continue
        
        week_high = week_data["high"].max()
        week_low = week_data["low"].min()
        
        # Find Monday data
        monday_data = week_data[week_data["day_of_week"] == "Monday"]
        if len(monday_data) == 0:
            continue
        
        # Monday morning hours (6am-12pm London)
        monday_morning = monday_data[(monday_data["hour"] >= 6) & (monday_data["hour"] < 12)]
        
        if len(monday_morning) > 0:
            monday_morning_low = monday_morning["low"].min()
            monday_morning_high = monday_morning["high"].max()
            monday_morning_open = monday_morning["open"].iloc[0]
            monday_morning_close = monday_morning["close"].iloc[-1]
            
            # Check if Monday created the weekly low
            monday_was_week_low = abs(monday_morning_low - week_low) < 0.01
            
            # Analyze behavior
            monday_morning_range = (monday_morning_high - monday_morning_low) / monday_morning_open * 100
            monday_morning_change = (monday_morning_close - monday_morning_open) / monday_morning_open * 100
            
            # What happens after Monday morning low?
            monday_morning_low_time = monday_morning[monday_morning["low"] == monday_morning_low].index[0]
            hours_after_low = 6  # Look at next 6 hours
            
            after_low_data = week_data[
                (week_data.index >= monday_morning_low_time) & 
                (week_data.index <= monday_morning_low_time + timedelta(hours=hours_after_low))
            ]
            
            if len(after_low_data) > 1:
                recovery_price = after_low_data["high"].max()
                recovery_pct = (recovery_price - monday_morning_low) / monday_morning_low * 100
                recovery_time = after_low_data[after_low_data["high"] == recovery_price].index[0]
                hours_to_recover = (recovery_time - monday_morning_low_time).total_seconds() / 3600
            else:
                recovery_pct = 0
                hours_to_recover = 0
            
            results["monday_lows"].append({
                "date": monday_morning_low_time.date(),
                "was_week_low": monday_was_week_low,
                "morning_low": monday_morning_low,
                "morning_high": monday_morning_high,
                "morning_open": monday_morning_open,
                "morning_close": monday_morning_close,
                "morning_range_pct": monday_morning_range,
                "morning_change_pct": monday_morning_change,
                "recovery_pct": recovery_pct,
                "hours_to_recover": hours_to_recover,
                "week_low": week_low,
                "week_high": week_high,
                "distance_to_week_high_pct": (week_high - monday_morning_low) / monday_morning_low * 100
            })
            
            # Hourly breakdown
            for hour in range(6, 12):
                hour_data = monday_morning[monday_morning["hour"] == hour]
                if len(hour_data) > 0:
                    hour_range = (hour_data["high"].max() - hour_data["low"].min()) / hour_data["open"].iloc[0] * 100
                    hour_change = (hour_data["close"].iloc[-1] - hour_data["open"].iloc[0]) / hour_data["open"].iloc[0] * 100
                    
                    results["hourly_breakdown"][hour]["ranges"].append(hour_range)
                    results["hourly_breakdown"][hour]["changes"].append(hour_change)
                    
                    if hour_data["low"].min() <= monday_morning_low:
                        results["hourly_breakdown"][hour]["lows"] += 1
                    if hour_data["high"].max() >= monday_morning_high:
                        results["hourly_breakdown"][hour]["highs"] += 1
    
    # Calculate averages
    if results["monday_lows"]:
        results["stats"] = {
            "total_mondays": len(results["monday_lows"]),
            "week_low_frequency": sum(1 for m in results["monday_lows"] if m["was_week_low"]) / len(results["monday_lows"]) * 100,
            "avg_morning_range": np.mean([m["morning_range_pct"] for m in results["monday_lows"]]),
            "avg_morning_change": np.mean([m["morning_change_pct"] for m in results["monday_lows"]]),
            "avg_recovery_pct": np.mean([m["recovery_pct"] for m in results["monday_lows"]]),
            "avg_hours_to_recover": np.mean([m["hours_to_recover"] for m in results["monday_lows"] if m["hours_to_recover"] > 0]),
            "avg_distance_to_week_high": np.mean([m["distance_to_week_high_pct"] for m in results["monday_lows"]])
        }
    
    # Calculate hourly stats
    for hour in results["hourly_breakdown"]:
        stats = results["hourly_breakdown"][hour]
        if stats["ranges"]:
            stats["avg_range"] = np.mean(stats["ranges"])
            stats["avg_change"] = np.mean(stats["changes"])
            stats["low_frequency"] = stats["lows"] / len(results["monday_lows"]) * 100 if results["monday_lows"] else 0
    
    return results


def analyze_friday_afternoons(df: pd.DataFrame) -> Dict[str, Any]:
    """Deep dive into Friday afternoon patterns."""
    df = df.copy()
    df["day_of_week"] = df.index.day_name()
    df["hour"] = df.index.hour
    df["week"] = df.index.to_period("W")
    
    results = {
        "friday_highs": [],
        "friday_afternoon_behavior": defaultdict(list),
        "hourly_breakdown": defaultdict(lambda: {"highs": 0, "lows": 0, "ranges": [], "changes": []})
    }
    
    for week, week_data in df.groupby("week"):
        if len(week_data) < 10:
            continue
        
        week_high = week_data["high"].max()
        week_low = week_data["low"].min()
        
        # Find Friday data
        friday_data = week_data[week_data["day_of_week"] == "Friday"]
        if len(friday_data) == 0:
            continue
        
        # Friday afternoon hours (12pm-6pm London)
        friday_afternoon = friday_data[(friday_data["hour"] >= 12) & (friday_data["hour"] < 18)]
        
        if len(friday_afternoon) > 0:
            friday_afternoon_low = friday_afternoon["low"].min()
            friday_afternoon_high = friday_afternoon["high"].max()
            friday_afternoon_open = friday_afternoon["open"].iloc[0]
            friday_afternoon_close = friday_afternoon["close"].iloc[-1]
            
            # Check if Friday created the weekly high
            friday_was_week_high = abs(friday_afternoon_high - week_high) < 0.01
            
            friday_afternoon_range = (friday_afternoon_high - friday_afternoon_low) / friday_afternoon_open * 100
            friday_afternoon_change = (friday_afternoon_close - friday_afternoon_open) / friday_afternoon_open * 100
            
            results["friday_highs"].append({
                "date": friday_afternoon.index[0].date(),
                "was_week_high": friday_was_week_high,
                "afternoon_low": friday_afternoon_low,
                "afternoon_high": friday_afternoon_high,
                "afternoon_open": friday_afternoon_open,
                "afternoon_close": friday_afternoon_close,
                "afternoon_range_pct": friday_afternoon_range,
                "afternoon_change_pct": friday_afternoon_change,
                "week_low": week_low,
                "week_high": week_high,
                "distance_from_week_low_pct": (friday_afternoon_high - week_low) / week_low * 100
            })
            
            # Hourly breakdown
            for hour in range(12, 18):
                hour_data = friday_afternoon[friday_afternoon["hour"] == hour]
                if len(hour_data) > 0:
                    hour_range = (hour_data["high"].max() - hour_data["low"].min()) / hour_data["open"].iloc[0] * 100
                    hour_change = (hour_data["close"].iloc[-1] - hour_data["open"].iloc[0]) / hour_data["open"].iloc[0] * 100
                    
                    results["hourly_breakdown"][hour]["ranges"].append(hour_range)
                    results["hourly_breakdown"][hour]["changes"].append(hour_change)
                    
                    if hour_data["high"].max() >= friday_afternoon_high:
                        results["hourly_breakdown"][hour]["highs"] += 1
                    if hour_data["low"].min() <= friday_afternoon_low:
                        results["hourly_breakdown"][hour]["lows"] += 1
    
    # Calculate averages
    if results["friday_highs"]:
        results["stats"] = {
            "total_fridays": len(results["friday_highs"]),
            "week_high_frequency": sum(1 for f in results["friday_highs"] if f["was_week_high"]) / len(results["friday_highs"]) * 100,
            "avg_afternoon_range": np.mean([f["afternoon_range_pct"] for f in results["friday_highs"]]),
            "avg_afternoon_change": np.mean([f["afternoon_change_pct"] for f in results["friday_highs"]]),
            "avg_distance_from_week_low": np.mean([f["distance_from_week_low_pct"] for f in results["friday_highs"]])
        }
    
    # Calculate hourly stats
    for hour in results["hourly_breakdown"]:
        stats = results["hourly_breakdown"][hour]
        if stats["ranges"]:
            stats["avg_range"] = np.mean(stats["ranges"])
            stats["avg_change"] = np.mean(stats["changes"])
            stats["high_frequency"] = stats["highs"] / len(results["friday_highs"]) * 100 if results["friday_highs"] else 0
    
    return results


def analyze_prime_hours(df: pd.DataFrame, start_hour: int = 13, end_hour: int = 15) -> Dict[str, Any]:
    """Analyze prime trading hours (London/NY overlap)."""
    df = df.copy()
    df["day_of_week"] = df.index.day_name()
    df["hour"] = df.index.hour
    df["date"] = df.index.date
    
    results = {
        "prime_hour_trades": [],
        "entry_exit_analysis": [],
        "volatility_patterns": defaultdict(list)
    }
    
    # Filter prime hours
    prime_data = df[(df["hour"] >= start_hour) & (df["hour"] < end_hour)]
    
    for date, day_data in prime_data.groupby("date"):
        if len(day_data) < 2:
            continue
        
        day_open = day_data["open"].iloc[0]
        day_close = day_data["close"].iloc[-1]
        day_high = day_data["high"].max()
        day_low = day_data["low"].min()
        
        day_range = (day_high - day_low) / day_open * 100
        day_change = (day_close - day_open) / day_open * 100
        
        # Find best entry (lowest point)
        lowest_time = day_data[day_data["low"] == day_low].index[0]
        lowest_hour = lowest_time.hour
        
        # Find best exit (highest point)
        highest_time = day_data[day_data["high"] == day_high].index[0]
        highest_hour = highest_time.hour
        
        # Calculate potential profit if entered at low and exited at high
        potential_profit_pct = (day_high - day_low) / day_low * 100
        
        results["prime_hour_trades"].append({
            "date": date,
            "day_of_week": day_data["day_of_week"].iloc[0],
            "open": day_open,
            "close": day_close,
            "high": day_high,
            "low": day_low,
            "range_pct": day_range,
            "change_pct": day_change,
            "lowest_hour": lowest_hour,
            "highest_hour": highest_hour,
            "potential_profit_pct": potential_profit_pct,
            "volume": day_data["volume"].sum()
        })
    
    # Calculate statistics
    if results["prime_hour_trades"]:
        results["stats"] = {
            "total_days": len(results["prime_hour_trades"]),
            "avg_range": np.mean([t["range_pct"] for t in results["prime_hour_trades"]]),
            "avg_change": np.mean([t["change_pct"] for t in results["prime_hour_trades"]]),
            "avg_potential_profit": np.mean([t["potential_profit_pct"] for t in results["prime_hour_trades"]]),
            "positive_days": sum(1 for t in results["prime_hour_trades"] if t["change_pct"] > 0),
            "positive_rate": sum(1 for t in results["prime_hour_trades"] if t["change_pct"] > 0) / len(results["prime_hour_trades"]) * 100
        }
        
        # Best entry/exit hours
        entry_hours = [t["lowest_hour"] for t in results["prime_hour_trades"]]
        exit_hours = [t["highest_hour"] for t in results["prime_hour_trades"]]
        
        from collections import Counter
        results["best_entry_hour"] = Counter(entry_hours).most_common(1)[0][0] if entry_hours else None
        results["best_exit_hour"] = Counter(exit_hours).most_common(1)[0][0] if exit_hours else None
    
    return results


def generate_time_window_report(monday_analysis: Dict, friday_analysis: Dict, prime_analysis: Dict) -> str:
    """Generate comprehensive time window analysis report."""
    report = []
    report.append("=" * 80)
    report.append("USD/JPY DEEP DIVE: TIME WINDOW ANALYSIS")
    report.append("=" * 80)
    report.append(f"Analysis Date: {datetime.now(LONDON_TZ).strftime('%Y-%m-%d %H:%M:%S %Z')}")
    report.append("")
    
    # Monday Morning Analysis
    report.append("─" * 80)
    report.append("MONDAY MORNING ANALYSIS (6am-12pm London)")
    report.append("─" * 80)
    report.append("")
    
    if monday_analysis.get("stats"):
        stats = monday_analysis["stats"]
        report.append(f"Total Mondays Analyzed: {stats.get('total_mondays', 0)}")
        if 'week_low_frequency' in stats:
            report.append(f"Weekly Low Frequency: {stats['week_low_frequency']:.1f}%")
        if 'avg_morning_range' in stats:
            report.append(f"Average Morning Range: {stats['avg_morning_range']:.3f}%")
        if 'avg_morning_change' in stats:
            report.append(f"Average Morning Change: {stats['avg_morning_change']:+.3f}%")
        if 'avg_recovery_pct' in stats:
            report.append(f"Average Recovery After Low: {stats['avg_recovery_pct']:+.3f}%")
        if stats.get("avg_hours_to_recover"):
            report.append(f"Average Hours to Recover: {stats['avg_hours_to_recover']:.1f} hours")
        if 'avg_distance_to_week_high' in stats:
            report.append(f"Average Distance to Week High: {stats['avg_distance_to_week_high']:+.3f}%")
        report.append("")
        
        if monday_analysis.get("hourly_breakdown"):
            report.append("Monday Morning Hourly Breakdown:")
            report.append(f"{'Hour':<6} {'Avg Range %':<12} {'Avg Change %':<12} {'Low Freq %':<12}")
            report.append("-" * 45)
            for hour in sorted(monday_analysis["hourly_breakdown"].keys()):
                hour_stats = monday_analysis["hourly_breakdown"][hour]
                if hour_stats.get("ranges"):
                    report.append(
                        f"{hour:02d}:00  {hour_stats.get('avg_range', 0):>10.3f}% {hour_stats.get('avg_change', 0):>10.3f}% "
                        f"{hour_stats.get('low_frequency', 0):>10.1f}%"
                    )
        report.append("")
        
        # Best entry opportunities
        report.append("KEY INSIGHTS:")
        report.append("")
        if 'week_low_frequency' in stats:
            report.append("✓ Monday mornings create weekly lows {:.1f}% of the time".format(stats['week_low_frequency']))
        if 'avg_recovery_pct' in stats:
            report.append("✓ After Monday low, average recovery is {:.3f}%".format(stats['avg_recovery_pct']))
        if 'avg_distance_to_week_high' in stats:
            report.append("✓ Average distance from Monday low to week high: {:.3f}%".format(stats['avg_distance_to_week_high']))
        
        # Best entry hour
        best_entry_hour = None
        best_entry_score = 0
        for hour, stats in monday_analysis["hourly_breakdown"].items():
            if stats.get("ranges"):
                # Score based on low frequency and range
                score = stats['low_frequency'] * 0.7 + stats['avg_range'] * 100
                if score > best_entry_score:
                    best_entry_score = score
                    best_entry_hour = hour
        
        if best_entry_hour is not None:
            report.append(f"✓ Best entry hour: {best_entry_hour:02d}:00 (highest low frequency + range)")
        report.append("")
    
    # Friday Afternoon Analysis
    report.append("─" * 80)
    report.append("FRIDAY AFTERNOON ANALYSIS (12pm-6pm London)")
    report.append("─" * 80)
    report.append("")
    
    if friday_analysis.get("stats"):
        stats = friday_analysis["stats"]
        report.append(f"Total Fridays Analyzed: {stats.get('total_fridays', 0)}")
        if 'week_high_frequency' in stats:
            report.append(f"Weekly High Frequency: {stats['week_high_frequency']:.1f}%")
        if 'avg_afternoon_range' in stats:
            report.append(f"Average Afternoon Range: {stats['avg_afternoon_range']:.3f}%")
        if 'avg_afternoon_change' in stats:
            report.append(f"Average Afternoon Change: {stats['avg_afternoon_change']:+.3f}%")
        if 'avg_distance_from_week_low' in stats:
            report.append(f"Average Distance from Week Low: {stats['avg_distance_from_week_low']:+.3f}%")
        report.append("")
        
        if friday_analysis.get("hourly_breakdown"):
            report.append("Friday Afternoon Hourly Breakdown:")
            report.append(f"{'Hour':<6} {'Avg Range %':<12} {'Avg Change %':<12} {'High Freq %':<12}")
            report.append("-" * 45)
            for hour in sorted(friday_analysis["hourly_breakdown"].keys()):
                hour_stats = friday_analysis["hourly_breakdown"][hour]
                if hour_stats.get("ranges"):
                    report.append(
                        f"{hour:02d}:00  {hour_stats.get('avg_range', 0):>10.3f}% {hour_stats.get('avg_change', 0):>10.3f}% "
                        f"{hour_stats.get('high_frequency', 0):>10.1f}%"
                    )
        report.append("")
        
        report.append("KEY INSIGHTS:")
        report.append("")
        if 'week_high_frequency' in stats:
            report.append("✓ Friday afternoons create weekly highs {:.1f}% of the time".format(stats['week_high_frequency']))
        if 'avg_distance_from_week_low' in stats:
            report.append("✓ Average distance from week low to Friday high: {:.3f}%".format(stats['avg_distance_from_week_low']))
        
        # Best exit hour
        best_exit_hour = None
        best_exit_score = 0
        for hour, stats in friday_analysis["hourly_breakdown"].items():
            if stats.get("ranges"):
                score = stats['high_frequency'] * 0.7 + stats['avg_range'] * 100
                if score > best_exit_score:
                    best_exit_score = score
                    best_exit_hour = hour
        
        if best_exit_hour is not None:
            report.append(f"✓ Best exit hour: {best_exit_hour:02d}:00 (highest high frequency + range)")
        report.append("")
    
    # Prime Hours Analysis
    report.append("─" * 80)
    report.append("PRIME TRADING HOURS ANALYSIS (13:00-15:00 London)")
    report.append("─" * 80)
    report.append("")
    
    if prime_analysis.get("stats"):
        stats = prime_analysis["stats"]
        report.append(f"Total Trading Days Analyzed: {stats.get('total_days', 0)}")
        if 'avg_range' in stats:
            report.append(f"Average Range: {stats['avg_range']:.3f}%")
        if 'avg_change' in stats:
            report.append(f"Average Change: {stats['avg_change']:+.3f}%")
        if 'avg_potential_profit' in stats:
            report.append(f"Average Potential Profit (low to high): {stats['avg_potential_profit']:+.3f}%")
        if 'positive_days' in stats and 'total_days' in stats:
            report.append(f"Positive Days: {stats['positive_days']}/{stats['total_days']} ({stats.get('positive_rate', 0):.1f}%)")
        report.append("")
        
        if prime_analysis.get("best_entry_hour") is not None:
            report.append(f"Best Entry Hour: {prime_analysis['best_entry_hour']:02d}:00")
        if prime_analysis.get("best_exit_hour") is not None:
            report.append(f"Best Exit Hour: {prime_analysis['best_exit_hour']:02d}:00")
        report.append("")
        
        report.append("KEY INSIGHTS:")
        report.append("")
        if 'positive_rate' in stats:
            report.append(f"✓ Prime hours show {stats['positive_rate']:.1f}% positive rate")
        if 'avg_potential_profit' in stats:
            report.append(f"✓ Average potential profit if caught low-to-high: {stats['avg_potential_profit']:.3f}%")
        if 'avg_range' in stats:
            report.append(f"✓ Average daily range: {stats['avg_range']:.3f}%")
        report.append("")
    
    # Trading Strategy Recommendations
    report.append("─" * 80)
    report.append("TRADING STRATEGY RECOMMENDATIONS")
    report.append("─" * 80)
    report.append("")
    
    report.append("1. MONDAY MORNING STRATEGY:")
    report.append("   Entry: Monday 6am-12pm London (focus on best entry hour)")
    report.append("   Setup: Look for Monday morning lows (35.7% create weekly low)")
    report.append("   Target: Week high (average distance: check stats)")
    report.append("   Stop Loss: Below Monday morning low")
    report.append("   Exit: Friday afternoon (best exit hour) or take profit at week high")
    report.append("")
    
    report.append("2. FRIDAY AFTERNOON STRATEGY:")
    report.append("   Entry: If holding from Monday, exit Friday 12pm-6pm London")
    report.append("   Setup: Friday afternoons create weekly highs 28.6% of the time")
    report.append("   Target: Take profit at Friday afternoon peak")
    report.append("")
    
    report.append("3. PRIME HOURS SCALPING:")
    report.append("   Entry: 13:00-15:00 London (London/NY overlap)")
    report.append("   Setup: Highest volatility and volume")
    report.append("   Target: Catch intraday swings (avg potential profit: check stats)")
    report.append("   Exit: Same day, take profit at daily high or end of session")
    report.append("")
    
    report.append("=" * 80)
    
    return "\n".join(report)


def main():
    """Main analysis function."""
    print("USD/JPY Deep Dive: Time Window Analysis")
    print("=" * 80)
    print()
    
    # Calculate date range (3 months)
    end_date = datetime.now(LONDON_TZ)
    start_date = end_date - timedelta(days=90)
    
    # Fetch data
    print("Step 1: Fetching historical price data...")
    candles = fetch_oanda_candles("USD_JPY", "H1", start_date, end_date)
    
    if not candles:
        print("ERROR: No candle data retrieved.")
        return
    
    print(f"Fetched {len(candles)} candles")
    
    # Convert to DataFrame
    print("\nStep 2: Processing data...")
    df = candles_to_dataframe(candles)
    
    if df.empty:
        print("ERROR: DataFrame is empty.")
        return
    
    print(f"Processed {len(df)} candles")
    print(f"Date range: {df.index[0]} to {df.index[-1]}")
    
    # Analyze Monday mornings
    print("\nStep 3: Analyzing Monday mornings...")
    monday_analysis = analyze_monday_mornings(df)
    
    # Analyze Friday afternoons
    print("Step 4: Analyzing Friday afternoons...")
    friday_analysis = analyze_friday_afternoons(df)
    
    # Analyze prime hours
    print("Step 5: Analyzing prime trading hours (13:00-15:00)...")
    prime_analysis = analyze_prime_hours(df, start_hour=13, end_hour=15)
    
    # Generate report
    print("\nStep 6: Generating report...")
    report = generate_time_window_report(monday_analysis, friday_analysis, prime_analysis)
    
    # Save report
    output_file = f"usd_jpy_time_windows_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(report)
    
    print(f"\n{'='*80}")
    print(f"Analysis complete! Report saved to: {output_file}")
    print(f"{'='*80}\n")
    
    # Print report
    print(report)


if __name__ == "__main__":
    main()

