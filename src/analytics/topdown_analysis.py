import logging
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from typing import Dict, List, Any

# Assuming these components exist based on the guide and previous context
from ..core.oanda_client import OandaClient
# from ..core.news_integration import get_news_manager # Temporarily remove to break dependency cycle

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TopDownAnalyzer:
    """
    Core analysis engine for the Top-Down Analysis Framework.
    Generates monthly, weekly, and mid-week market roadmaps.
    """
    def __init__(self, oanda_client: OandaClient, news_manager=None): # Make news_manager optional
        self.oanda_client = oanda_client
        self.news_manager = news_manager # It will be None for now, but won't crash
        self.instruments = [
            'EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD',
            'USD_CAD', 'NZD_USD', 'XAU_USD',
        ]
        logger.info("✅ TopDownAnalyzer initialized.")

    def _get_historical_data(self, instrument: str, timeframe: str) -> pd.DataFrame:
        """Fetches and prepares historical data from OANDA."""
        if timeframe == "monthly":
            granularity = "M"
            count = 12
        elif timeframe == "weekly":
            granularity = "W"
            count = 52
        else: # daily for execution context
            granularity = "D"
            count = 100

        try:
            candles = self.oanda_client.get_candles(instrument, granularity=granularity, count=count)
            if not candles or 'candles' not in candles or not candles['candles']:
                return pd.DataFrame()

            df = pd.DataFrame(candles['candles'])
            df['time'] = pd.to_datetime(df['time'])
            df.set_index('time', inplace=True)
            
            # Convert 'mid' prices from dict to columns
            df['open'] = df['mid'].apply(lambda x: float(x['o']))
            df['high'] = df['mid'].apply(lambda x: float(x['h']))
            df['low'] = df['mid'].apply(lambda x: float(x['l']))
            df['close'] = df['mid'].apply(lambda x: float(x['c']))
            df.drop(columns=['mid', 'complete', 'volume'], inplace=True)
            
            return df
        except Exception as e:
            logger.error(f"❌ Error fetching historical data for {instrument}: {e}")
            return pd.DataFrame()

    def _calculate_indicators(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculates technical indicators based on the provided dataframe."""
        if df.empty or len(df) < 50:
            return {}

        # EMAs for Trend Identification
        ema_short = df['close'].ewm(span=20, adjust=False).mean().iloc[-1]
        ema_long = df['close'].ewm(span=50, adjust=False).mean().iloc[-1]

        # ATR for Volatility and Price Targets
        tr = pd.DataFrame()
        tr['h-l'] = df['high'] - df['low']
        tr['h-pc'] = abs(df['high'] - df['close'].shift(1))
        tr['l-pc'] = abs(df['low'] - df['close'].shift(1))
        tr['tr'] = tr[['h-l', 'h-pc', 'l-pc']].max(axis=1)
        atr = tr['tr'].rolling(window=14).mean().iloc[-1]

        # ADX-like Trend Strength
        plus_dm = df['high'].diff()
        minus_dm = df['low'].diff().abs()
        plus_di = 100 * (plus_dm.ewm(alpha=1/14).mean() / atr)
        minus_di = 100 * (minus_dm.ewm(alpha=1/14).mean() / atr)
        dx = 100 * (abs(plus_di - minus_di) / (plus_di + minus_di)).ewm(alpha=1/14).mean()
        adx = dx.iloc[-1] if not pd.isna(dx.iloc[-1]) else 0.0

        return {
            "ema_short": ema_short,
            "ema_long": ema_long,
            "atr": atr,
            "adx": adx,
        }

    def _get_key_levels(self, df: pd.DataFrame) -> List[float]:
        """Identifies key support and resistance levels."""
        if df.empty or len(df) < 20:
            return []
        recent_df = df.tail(20)
        swing_high = recent_df['high'].max()
        swing_low = recent_df['low'].min()
        return sorted([swing_low, swing_high])

    def perform_instrument_analysis(self, instrument: str, timeframe: str) -> Dict[str, Any]:
        """Performs a full top-down analysis for a single instrument."""
        df = self._get_historical_data(instrument, timeframe)
        if df.empty:
            return {"error": "Could not fetch historical data."}

        indicators = self._calculate_indicators(df)
        if not indicators:
            return {"error": "Not enough data for analysis."}
            
        # 1. Trend Identification
        bias = "NEUTRAL"
        if indicators["ema_short"] > indicators["ema_long"]:
            bias = "BULLISH"
        elif indicators["ema_short"] < indicators["ema_long"]:
            bias = "BEARISH"

        # 2. Trend Strength
        strength = min(1.0, indicators["adx"] / 50.0) # Normalize ADX

        # 3. Key Levels
        key_levels = self._get_key_levels(df)

        # 4. Price Targets
        atr = indicators["atr"]
        multipliers = (2.0, 4.0) if timeframe == "monthly" else (1.0, 2.0)
        
        current_price = df['close'].iloc[-1]
        if bias == "BULLISH":
            targets = [current_price + (atr * m) for m in multipliers]
        elif bias == "BEARISH":
            targets = [current_price - (atr * m) for m in multipliers]
        else:
            targets = []

        return {
            "instrument": instrument,
            "bias": bias,
            "strength": strength,
            "key_levels": key_levels,
            "price_targets": targets,
            "current_price": current_price,
        }

    def generate_report(self, timeframe: str) -> Dict[str, Any]:
        """Generates a full market report for the specified timeframe."""
        report = {
            "timeframe": timeframe.upper(),
            "generated_at": datetime.utcnow().isoformat(),
            "global_sentiment": "MIXED", # Placeholder, requires macro analysis
            "analysis": [],
            "recommendations": {"trade": [], "avoid": []}
        }
        
        instrument_sentiments = []
        for instrument in self.instruments:
            analysis = self.perform_instrument_analysis(instrument, timeframe)
            if "error" not in analysis:
                report["analysis"].append(analysis)
                if analysis["strength"] > 0.4 and analysis["bias"] != "NEUTRAL":
                    report["recommendations"]["trade"].append(instrument)
                else:
                    report["recommendations"]["avoid"].append(instrument)
        
        # Determine global sentiment based on majority bias
        biases = [a["bias"] for a in report["analysis"]]
        bullish_count = biases.count("BULLISH")
        bearish_count = biases.count("BEARISH")
        if bullish_count > len(biases) * 0.6:
            report["global_sentiment"] = "RISK-ON"
        elif bearish_count > len(biases) * 0.6:
            report["global_sentiment"] = "RISK-OFF"

        return report

    def format_report_for_telegram(self, report: Dict[str, Any]) -> str:
        """Formats a generated report into a human-readable Telegram message."""
        timeframe = report["timeframe"]
        header = f"📅 {timeframe} TOP-DOWN ANALYSIS"
        if timeframe == "MID-WEEK":
            header = "📊 MID-WEEK MARKET UPDATE"

        lines = [
            header,
            f"Generated: {datetime.fromisoformat(report['generated_at']).strftime('%Y-%m-%d %H:%M UTC')}",
            "",
            f"🌍 Global Sentiment: {report['global_sentiment']}",
            ""
        ]

        if report["recommendations"]["trade"]:
            lines.append("✅ Recommended Pairs:")
            for analysis in report["analysis"]:
                if analysis["instrument"] in report["recommendations"]["trade"]:
                    lines.append(f"  • {analysis['instrument']}: {analysis['bias']} (Strength: {analysis['strength']:.0%})")
            lines.append("")

        if report["recommendations"]["avoid"]:
            lines.append("⚠️ Avoid:")
            lines.append(f"  • " + ", ".join(report["recommendations"]["avoid"]))
            lines.append("")

        if timeframe != "MID-WEEK" and report["recommendations"]["trade"]:
            lines.append("🎯 Key Price Targets:")
            for analysis in report["analysis"]:
                 if analysis["instrument"] in report["recommendations"]["trade"] and analysis["price_targets"]:
                     targets_str = " → ".join([f"{t:.4f}" for t in analysis["price_targets"]])
                     lines.append(f"  • {analysis['instrument']}: {targets_str} ({analysis['bias'].lower()})")
            lines.append("")

        lines.append("💡 Trading Tips:")
        lines.append("  • Trade during prime hours (1pm-5pm London)")
        lines.append("  • Use pullbacks to key levels for entries")
        lines.append("  • Respect stop losses and targets")

        return "\n".join(lines)

# Global instance and getter for easy integration
_topdown_analyzer = None

def get_topdown_analyzer(oanda_client=None, news_manager=None) -> TopDownAnalyzer:
    global _topdown_analyzer
    if _topdown_analyzer is None:
        if oanda_client is None:
            # This is a fallback for testing; in production, these should be passed.
            from ..core.oanda_client import get_oanda_client
            # from ..core.news_integration import get_news_manager # Temporarily remove
            oanda_client = get_oanda_client()
            # news_manager = get_news_manager() # Temporarily remove
        _topdown_analyzer = TopDownAnalyzer(oanda_client, news_manager=None) # Pass None
    return _topdown_analyzer
