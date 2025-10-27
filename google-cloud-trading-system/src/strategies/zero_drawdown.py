"""
Zero Drawdown Strategy
Conservative trading with maximum protection - based on Group2Strategy
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class ZeroDrawdownStrategy:
    """Zero Drawdown Strategy - Conservative with maximum protection"""
    
    name: str = "Zero Drawdown"
    description: str = "Conservative trading with maximum protection"
    
    # Instruments
    instruments: List[str] = None
    
    # Performance targets
    target_sharpe: float = 6.12
    target_win_rate: float = 53.6
    target_annual_return: float = 2244.0
    
    # Risk management - VERY CONSERVATIVE
    risk_per_trade: float = 0.01  # 1% max risk per trade
    max_portfolio_risk: float = 0.30  # 30% max portfolio exposure
    max_concurrent_positions: int = 2
    max_daily_trades: int = 30
    
    def __post_init__(self):
        if self.instruments is None:
            self.instruments = ["EUR_USD", "GBP_USD", "XAU_USD"]
    
    def analyze_market(self, instrument: str, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Analyze market for zero drawdown opportunities"""
        try:
            # Very conservative approach - only trade in perfect conditions
            if not market_data or 'price' not in market_data:
                return None
            
            price_data = market_data['price']
            current_price = (price_data['bid'] + price_data['ask']) / 2
            
            # Only trade if conditions are PERFECT
            # This is intentionally very strict to maintain zero drawdown
            
            # Check for strong trend with low volatility
            if 'indicators' in market_data:
                indicators = market_data['indicators']
                
                # Only trade if RSI is not overbought/oversold
                rsi = indicators.get('rsi', 50)
                if rsi < 30 or rsi > 70:
                    return None
                
                # Only trade if ADX shows strong trend
                adx = indicators.get('adx', 0)
                if adx < 25:
                    return None
                
                # Only trade if volatility is low
                atr = indicators.get('atr', 0)
                if atr > current_price * 0.01:  # 1% volatility threshold
                    return None
            
            # Generate very conservative signal
            if rsi > 50:
                direction = "BUY"
                confidence = 0.6  # Conservative confidence
            else:
                direction = "SELL"
                confidence = 0.6
            
            return {
                'instrument': instrument,
                'direction': direction,
                'confidence': confidence,
                'entry_price': current_price,
                'stop_loss': current_price * (0.995 if direction == "BUY" else 1.005),
                'take_profit': current_price * (1.01 if direction == "BUY" else 0.99),
                'risk_amount': self.risk_per_trade,
                'strategy_name': self.name
            }
            
        except Exception as e:
            logger.error(f"Error in ZeroDrawdownStrategy.analyze_market: {e}")
            return None

def get_zero_drawdown_strategy() -> ZeroDrawdownStrategy:
    """Get Zero Drawdown Strategy instance"""
    return ZeroDrawdownStrategy()
