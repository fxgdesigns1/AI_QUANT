#!/usr/bin/env python3
"""
Paper Broker - No-network broker for paper trading mode

Provides the same interface as OandaClient but never makes network calls.
Used when PAPER_ALLOW_OANDA_NETWORK=false or when broker credentials are missing.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .oanda_client import OandaAccount, OandaPrice, OandaOrder

logger = logging.getLogger(__name__)


class PaperBroker:
    """Paper broker that never makes network calls.
    
    Implements the same interface as OandaClient but returns synthetic data.
    Used for uninterrupted paper-mode testing without OANDA dependency.
    """
    
    def __init__(self, account_id: str, currency: str = "USD", initial_balance: float = 10000.0):
        """Initialize paper broker with dummy account data"""
        self.account_id = account_id
        self.currency = currency
        self.initial_balance = initial_balance
        self.current_prices: Dict[str, OandaPrice] = {}
        self.orders: Dict[str, OandaOrder] = {}
        
        logger.info(f"📄 PAPER BROKER initialized for account {account_id[-3:] if len(account_id) > 3 else account_id}")
        logger.info(f"   No network calls will be made; all data is synthetic")
    
    def get_account_info(self) -> OandaAccount:
        """Get synthetic account information"""
        return OandaAccount(
            account_id=self.account_id,
            currency=self.currency,
            balance=self.initial_balance,
            unrealized_pl=0.0,
            realized_pl=0.0,
            margin_used=0.0,
            margin_available=self.initial_balance,
            open_trade_count=0,
            open_position_count=0,
            pending_order_count=0
        )
    
    def get_current_price(self, instrument: str) -> OandaPrice:
        """Get synthetic current price for a single instrument"""
        prices = self.get_current_prices([instrument], force_refresh=False)
        return prices.get(instrument)
    
    def get_current_prices(self, instruments: List[str], force_refresh: bool = False) -> Dict[str, OandaPrice]:
        """Get synthetic current prices for instruments
        
        Returns deterministic synthetic prices based on instrument type.
        Never makes network calls.
        """
        prices = {}
        
        # Synthetic price generator (deterministic for testing)
        synthetic_prices = {
            'XAU_USD': (2650.0, 2650.5),  # Gold
            'EUR_USD': (1.0850, 1.0852),
            'GBP_USD': (1.2650, 1.2652),
            'USD_JPY': (149.50, 149.52),
            'AUD_USD': (0.6550, 0.6552),
            'USD_CAD': (1.3450, 1.3452),
            'NZD_USD': (0.6050, 0.6052),
        }
        
        for instrument in instruments:
            if instrument in self.current_prices and not force_refresh:
                # Return cached price
                prices[instrument] = self.current_prices[instrument]
            else:
                # Generate synthetic price
                if instrument in synthetic_prices:
                    bid, ask = synthetic_prices[instrument]
                else:
                    # Default synthetic price for unknown instruments
                    bid = 1.0
                    ask = 1.0002
                
                price = OandaPrice(
                    instrument=instrument,
                    bid=bid,
                    ask=ask,
                    timestamp=datetime.now(),
                    spread=ask - bid,
                    is_live=False  # Mark as paper/synthetic
                )
                prices[instrument] = price
                self.current_prices[instrument] = price
        
        logger.debug(f"📄 PAPER BROKER: Returning synthetic prices for {len(prices)} instruments")
        return prices
    
    def get_candles(self, instrument: str, granularity: str = 'M1', count: int = 50, price: str = 'BA') -> Dict[str, Any]:
        """Get synthetic candle data (for compatibility)
        
        Returns empty structure - strategies should use their own price history.
        """
        logger.debug(f"📄 PAPER BROKER: get_candles called for {instrument} (no network call)")
        return {
            'instrument': instrument,
            'granularity': granularity,
            'candles': []
        }
    
    def place_market_order(self, instrument: str, units: int, stop_loss: Optional[float] = None,
                          take_profit: Optional[float] = None) -> OandaOrder:
        """Place a simulated market order (no network call)"""
        order_id = f"paper_{len(self.orders) + 1:06d}"
        side = 'buy' if units > 0 else 'sell'
        
        order = OandaOrder(
            order_id=order_id,
            instrument=instrument,
            units=units,
            side=side,
            type='MARKET',
            price=None,
            stop_loss=stop_loss,
            take_profit=take_profit,
            time_in_force='IOC',
            status='FILLED',  # Paper orders are always "filled"
            create_time=datetime.now(),
            fill_time=datetime.now(),
            trade_id=f"paper_trade_{order_id}"
        )
        
        self.orders[order_id] = order
        logger.info(f"📄 PAPER BROKER: Simulated market order {order_id} - {instrument} {units} units")
        return order
    
    def create_order(self, instrument: str, units: int, side: str, order_type: str,
                     stop_loss: Optional[float] = None, take_profit: Optional[float] = None,
                     price: Optional[float] = None, time_in_force: str = 'FOK') -> OandaOrder:
        """Compatibility wrapper for OrderManager"""
        side_upper = (side or '').upper()
        ot = (order_type or 'MARKET').upper()
        signed_units = abs(int(units)) if side_upper == 'BUY' else -abs(int(units))
        
        if ot == 'MARKET':
            return self.place_market_order(instrument, signed_units, stop_loss, take_profit)
        else:
            # For LIMIT/STOP orders, use market order simulation
            logger.debug(f"📄 PAPER BROKER: {ot} order simulated as MARKET for {instrument}")
            return self.place_market_order(instrument, signed_units, stop_loss, take_profit)
    
    def place_limit_order(self, instrument: str, units: int, price: float,
                          time_in_force: str = 'GTC',
                          stop_loss: Optional[float] = None,
                          take_profit: Optional[float] = None) -> OandaOrder:
        """Place a simulated limit order"""
        return self.place_market_order(instrument, units, stop_loss, take_profit)
    
    def place_stop_order(self, instrument: str, units: int, price: float,
                         time_in_force: str = 'GTC',
                         stop_loss: Optional[float] = None,
                         take_profit: Optional[float] = None) -> OandaOrder:
        """Place a simulated stop order"""
        return self.place_market_order(instrument, units, stop_loss, take_profit)
