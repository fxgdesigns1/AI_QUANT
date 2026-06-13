import sys
import os
import json
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
load_dotenv("google-cloud-trading-system/.env") # Try alternative location

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# Import system components
try:
    from src.control_plane.market_data_provider import get_candles
    from src.control_plane.outlook_engine import OutlookEngine
except ImportError as e:
    print(f"Import Error: {e}")
    # Fallback/Mock for testing if imports fail in partial env
    class OutlookEngine:
        pass
    def get_candles(inst, granularity, count):
        return []

# Setup logging
LOG_FILE = os.path.join(os.getcwd(), "instrument_bias_probe.log")
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("bias_probe")

REPORT_FILE = os.path.join(os.getcwd(), "instrument_bias_probe.json")

def calculate_atr(df, period=14):
    high_low = df["high"] - df["low"]
    high_close = np.abs(df["high"] - df["close"].shift())
    low_close = np.abs(df["low"] - df["close"].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    return true_range.rolling(period).mean()

def calculate_adx(df, period=14):
    # Simplified ADX calculation for probe
    plus_dm = df["high"].diff()
    minus_dm = df["low"].diff()
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm > 0] = 0
    
    tr = calculate_atr(df, period)
    atr = tr.rolling(period).mean()
    
    plus_di = 100 * (plus_dm.ewm(alpha=1/period).mean() / atr)
    minus_di = 100 * (minus_dm.ewm(alpha=1/period).mean() / atr)
    dx = (np.abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
    adx = dx.rolling(period).mean()
    return adx

def analyze_instrument(instrument):
    logger.info(f"--- Analyzing {instrument} ---")
    
    # 1. Load Data
    # Fetch H1 candles for the last 90 days to establish ATR baseline
    # Note: get_candles signature might vary, assuming standard here
    try:
        candles = get_candles(instrument, granularity="H1", count=24*90) 
    except Exception as e:
        logger.error(f"Error fetching candles: {e}")
        return None

    if not candles:
        logger.error(f"No data found for {instrument}")
        return None

    # Convert to DataFrame
    # Assuming candle objects have mid/c, mid/h etc or flat attributes
    # Adjust based on actual object structure. Often it's .mid.c or .c if flattened.
    # We'll try generic attribute access
    data_list = []
    for c in candles:
        # HACK: Inspect object structure dynamically
        try:
            d = {
                "time": c.time,
                "open": float(c.mid.o),
                "high": float(c.mid.h),
                "low": float(c.mid.l),
                "close": float(c.mid.c),
                "volume": float(c.volume)
            }
            data_list.append(d)
        except:
            # Fallback if flat
            try:
                d = {
                    "time": c.time,
                    "open": float(c.o),
                    "high": float(c.h),
                    "low": float(c.l),
                    "close": float(c.c),
                    "volume": float(c.volume)
                }
                data_list.append(d)
            except:
                pass

    if not data_list:
        logger.error("Failed to parse candle data")
        return None

    df = pd.DataFrame(data_list)
    df["time"] = pd.to_datetime(df["time"])
    df.set_index("time", inplace=True)
    
    current_price = df["close"].iloc[-1]
    
    # 2. Compute % Moves
    price_24h_ago = df["close"].iloc[-24] if len(df) >= 24 else df["close"].iloc[0]
    price_72h_ago = df["close"].iloc[-72] if len(df) >= 72 else df["close"].iloc[0]
    
    move_24h_pct = ((current_price - price_24h_ago) / price_24h_ago) * 100
    move_72h_pct = ((current_price - price_72h_ago) / price_72h_ago) * 100
    
    logger.info(f"Price: {current_price}")
    logger.info(f"24h Move: {move_24h_pct:.2f}%")
    logger.info(f"72h Move: {move_72h_pct:.2f}%")

    # 3. ATR Analysis
    df["atr"] = calculate_atr(df)
    current_atr = df["atr"].iloc[-1]
    
    # Calculate ATR percentile (volatility regime)
    atr_history = df["atr"].dropna()
    atr_percentile = (atr_history < current_atr).mean() * 100
    
    logger.info(f"ATR(14) H1: {current_atr:.4f}")
    logger.info(f"ATR Percentile (vs 90d): {atr_percentile:.1f}%")
    
    is_shock = atr_percentile > 95
    if is_shock:
        logger.warning(f"⚠️ SHOCK DETECTED: ATR percentile > 95%")

    # 4. ADX & Trend
    df["adx"] = calculate_adx(df)
    current_adx = df["adx"].iloc[-1]
    logger.info(f"ADX(14): {current_adx:.2f}")
    
    regime = "RANGING"
    if current_adx > 25:
        regime = "TRENDING"
    if is_shock:
        regime = "SHOCK"
        
    logger.info(f"Regime Class: {regime}")

    # 5. Bias Logic Simulation
    # XAU specific thresholds often differ
    is_gold = "XAU" in instrument
    
    # Define thresholds explicitly
    threshold_adx_trend = 25.0
    threshold_shock_atr = 95.0
    
    bias = "NEUTRAL"
    reason = "Unknown"
    
    if is_shock:
        bias = "NEUTRAL"
        reason = f"Shock Volatility (ATR% {atr_percentile:.1f} > {threshold_shock_atr})"
    elif current_adx < threshold_adx_trend:
        bias = "NEUTRAL" 
        reason = f"Weak Trend (ADX {current_adx:.1f} < {threshold_adx_trend})"
    else:
        # Check direction via EMA
        ema_short = df["close"].ewm(span=50).mean().iloc[-1]
        ema_long = df["close"].ewm(span=200).mean().iloc[-1]
        
        logger.info(f"EMA50: {ema_short:.4f}, EMA200: {ema_long:.4f}")

        if current_price > ema_short > ema_long:
            bias = "BULLISH"
            reason = "Trend Alignment (Price > EMA50 > EMA200)"
        elif current_price < ema_short < ema_long:
            bias = "BEARISH" 
            reason = "Trend Alignment (Price < EMA50 < EMA200)"
        else:
            bias = "NEUTRAL"
            reason = "Messy EMA Structure (EMAs not aligned)"
            
    logger.info(f"Calculated Bias: {bias}")
    logger.info(f"Reason: {reason}")
    
    return {
        "instrument": instrument,
        "price": current_price,
        "move_24h_pct": move_24h_pct,
        "move_72h_pct": move_72h_pct,
        "atr": current_atr,
        "atr_percentile": atr_percentile,
        "adx": current_adx,
        "regime": regime,
        "bias": bias,
        "reason": reason,
        "is_gold": is_gold
    }

def main():
    instruments = ["XAU_USD", "EUR_USD", "GBP_USD", "USD_JPY", "GBP_JPY"]
    results = []
    
    for inst in instruments:
        try:
            res = analyze_instrument(inst)
            if res:
                results.append(res)
        except Exception as e:
            logger.error(f"Failed to analyze {inst}: {e}")
            import traceback
            traceback.print_exc()

    # Save Report
    with open(REPORT_FILE, "w") as f:
        json.dump({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "results": results
        }, f, indent=2)
    
    logger.info(f"Report saved to {REPORT_FILE}")
    
    # Comparison Summary
    logger.info("\n=== COMPARISON SUMMARY ===")
    print(f"{'Instrument':<10} | {'24h %':<8} | {'ADX':<6} | {'ATR %':<6} | {'Regime':<10} | {'Bias':<10}")
    print("-" * 75)
    for r in results:
        print(f"{r['instrument']:<10} | {r['move_24h_pct']:>7.2f}% | {r['adx']:>6.1f} | {r['atr_percentile']:>5.1f}% | {r['regime']:<10} | {r['bias']:<10}")

if __name__ == "__main__":
    main()
