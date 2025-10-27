"""
High Frequency Strategy
Multiple small trades with quick profits - based on Group1Strategy
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class HighFrequencyStrategy:
    """High Frequency Strategy - Multiple small trades with quick profits"""
    
    name: str = "High Frequency"
    description: str = "Multiple small trades with quick profits"
    
    # Instruments
    instruments: List[str] = None
    
    # Performance targets
    target_sharpe: float = 38.5
    target_win_rate: float = 79.7
    target_annual_return: float = 148.0
    
    # Risk management - MODERATE
    risk_per_trade: float = 0.01  # 1% max risk per trade
    max_portfolio_risk: float = 0.40  # 40% max portfolio exposure
    max_concurrent_positions: int = 2
    max_daily_trades: int = 30
    
    def __post_init__(self):
        if self.instruments is None:
            self.instruments = ["EUR_USD", "GBP_USD", "XAU_USD"]
    
    def analyze_market(self, instrument: str, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Analyze market for high frequency opportunities"""
        try:
            if not market_data or 'price' not in market_data:
                return None
            
            price_data = market_data['price']
            current_price = (price_data['bid'] + price_data['ask']) / 2
            
            # High frequency approach - trade on smaller moves
            if 'indicators' in market_data:
                indicators = market_data['indicators']
                
                # RSI for momentum
                rsi = indicators.get('rsi', 50)
                
                # MACD for trend
                macd = indicators.get('macd', 0)
                macd_signal = indicators.get('macd_signal', 0)
                
                # High frequency - trade on smaller signals
                if rsi > 45 and macd > macd_signal:
                    direction = "BUY"
                    confidence = 0.7
                elif rsi < 55 and macd < macd_signal:
                    direction = "SELL"
                    confidence = 0.7
                else:
                    return None
            else:
                # Fallback to simple momentum
                direction = "BUY" if current_price > 1.0 else "SELL"
                confidence = 0.6
            
            return {
                'instrument': instrument,
                'direction': direction,
                'confidence': confidence,
                'entry_price': current_price,
                'stop_loss': current_price * (0.999 if direction == "BUY" else 1.001),
                'take_profit': current_price * (1.002 if direction == "BUY" else 0.998),
                'risk_amount': self.risk_per_trade,
                'strategy_name': self.name
            }
            
        except Exception as e:
            logger.error(f"Error in HighFrequencyStrategy.analyze_market: {e}")
            return None

def get_high_frequency_strategy() -> HighFrequencyStrategy:
    """Get High Frequency Strategy instance"""
    return HighFrequencyStrategy()
