"""
High Win Rate Strategy
High probability setups with tight risk control - based on Group3Strategy
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class HighWinRateStrategy:
    """High Win Rate Strategy - High probability setups with tight risk control"""
    
    name: str = "High Win Rate"
    description: str = "High probability setups with tight risk control"
    
    # Instruments
    instruments: List[str] = None
    
    # Performance targets
    target_sharpe: float = 38.85
    target_win_rate: float = 82.4
    target_annual_return: float = 113.9
    
    # Risk management - MODERATE
    risk_per_trade: float = 0.015  # 1.5% max risk per trade
    max_portfolio_risk: float = 0.40  # 40% max portfolio exposure
    max_concurrent_positions: int = 2
    max_daily_trades: int = 40
    
    def __post_init__(self):
        if self.instruments is None:
            self.instruments = ["EUR_USD", "GBP_USD", "XAU_USD"]
    
    def analyze_market(self, instrument: str, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Analyze market for high win rate opportunities"""
        try:
            if not market_data or 'price' not in market_data:
                return None
            
            price_data = market_data['price']
            current_price = (price_data['bid'] + price_data['ask']) / 2
            
            # High win rate approach - only trade in very favorable conditions
            if 'indicators' in market_data:
                indicators = market_data['indicators']
                
                # RSI must be in favorable zone (30-70)
                rsi = indicators.get('rsi', 50)
                if rsi < 30 or rsi > 70:
                    return None
                
                # ADX must show strong trend
                adx = indicators.get('adx', 0)
                if adx < 30:
                    return None
                
                # MACD must be bullish/bearish
                macd = indicators.get('macd', 0)
                macd_signal = indicators.get('macd_signal', 0)
                
                if macd > macd_signal:
                    direction = "BUY"
                    confidence = 0.8  # High confidence for high win rate
                elif macd < macd_signal:
                    direction = "SELL"
                    confidence = 0.8
                else:
                    return None
            else:
                # Fallback to simple momentum
                direction = "BUY" if current_price > 1.0 else "SELL"
                confidence = 0.7
            
            return {
                'instrument': instrument,
                'direction': direction,
                'confidence': confidence,
                'entry_price': current_price,
                'stop_loss': current_price * (0.998 if direction == "BUY" else 1.002),
                'take_profit': current_price * (1.005 if direction == "BUY" else 0.995),
                'risk_amount': self.risk_per_trade,
                'strategy_name': self.name
            }
            
        except Exception as e:
            logger.error(f"Error in HighWinRateStrategy.analyze_market: {e}")
            return None

def get_high_win_rate_strategy() -> HighWinRateStrategy:
    """Get High Win Rate Strategy instance"""
    return HighWinRateStrategy()
