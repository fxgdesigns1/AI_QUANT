#!/usr/bin/env python3
"""
OANDA API Client for Live Trading
Production-ready OANDA API integration for Google Cloud deployment
"""

import os
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import requests
from dataclasses import dataclass, asdict
import threading
import queue
import re

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class OandaAccount:
    """OANDA account information"""
    account_id: str
    currency: str
    balance: float
    unrealized_pl: float
    realized_pl: float
    margin_used: float
    margin_available: float
    open_trade_count: int
    open_position_count: int
    pending_order_count: int

@dataclass
class OandaPrice:
    """OANDA price data"""
    instrument: str
    bid: float
    ask: float
    timestamp: datetime
    spread: float
    is_live: bool = True

@dataclass
class OandaOrder:
    """OANDA order information"""
    order_id: str
    instrument: str
    units: int
    side: str  # 'buy' or 'sell'
    type: str  # 'MARKET', 'LIMIT', 'STOP', etc.
    price: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    time_in_force: str
    status: str
    create_time: datetime
    fill_time: Optional[datetime] = None
    trade_id: Optional[str] = None

@dataclass
class OandaPosition:
    """OANDA position information"""
    instrument: str
    long_units: int
    short_units: int
    long_unrealized_pl: float
    short_unrealized_pl: float
    long_margin_used: float
    short_margin_used: float
    long_avg_price: Optional[float]
    short_avg_price: Optional[float]
    unrealized_pl: float
    margin_used: float

class OandaClient:
    """Production OANDA API Client for Google Cloud deployment"""
    
    def __init__(self, api_key: str = None, account_id: str = None, environment: str = None):
        """Initialize OANDA client with credentials - FIXED: Uses unified credential loader"""
        # Try unified credential loader first
        try:
            from .unified_credential_loader import get_oanda_api_key, get_oanda_account_id, ensure_credentials_loaded
            ensure_credentials_loaded()
            self.api_key = api_key or get_oanda_api_key()
            self.account_id = account_id or get_oanda_account_id()
        except Exception as e:
            logger.debug(f"Unified credential loader not available: {e}")
            # Fallback to environment variables
            self.api_key = api_key or os.getenv('OANDA_API_KEY')
            self.account_id = account_id or os.getenv('OANDA_ACCOUNT_ID') or os.getenv('PRIMARY_ACCOUNT')
        
        self.environment = environment or os.getenv('OANDA_ENVIRONMENT', 'practice')
        
        # Final validation with helpful error message
        if not self.api_key or not self.account_id:
            error_msg = "API key and account ID must be provided. "
            error_msg += "Tried: unified loader, environment variables, and hardcoded values."
            if not self.api_key:
                error_msg += " API_KEY missing."
            if not self.account_id:
                error_msg += " ACCOUNT_ID missing."
            raise ValueError(error_msg)
        
        # Set base URL based on environment
        if self.environment == 'practice':
            self.base_url = 'https://api-fxpractice.oanda.com'
            self.stream_url = 'https://stream-fxpractice.oanda.com'
        else:
            self.base_url = 'https://api-fxtrade.oanda.com'
            self.stream_url = 'https://stream-fxtrade.oanda.com'
        
        # API endpoints
        self.accounts_endpoint = f"{self.base_url}/v3/accounts"
        self.pricing_endpoint = f"{self.base_url}/v3/accounts/{self.account_id}/pricing"
        self.orders_endpoint = f"{self.base_url}/v3/accounts/{self.account_id}/orders"
        self.positions_endpoint = f"{self.base_url}/v3/accounts/{self.account_id}/positions"
        self.trades_endpoint = f"{self.base_url}/v3/accounts/{self.account_id}/trades"
        self.instruments_endpoint = f"{self.base_url}/v3/instruments"
        
        # Headers for API requests
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 100ms between requests
        
        # Data storage
        self.current_prices: Dict[str, OandaPrice] = {}
        self.account_info: Optional[OandaAccount] = None
        self.positions: Dict[str, OandaPosition] = {}
        self.orders: Dict[str, OandaOrder] = {}
        
        # Streaming
        self.streaming = False
        self.stream_thread: Optional[threading.Thread] = None
        self.price_queue = queue.Queue()
        
        logger.info(f"✅ OANDA client initialized for {self.environment} environment")
        logger.info(f"📊 Account ID: {self.account_id}")
    
    def _rate_limit(self):
        """Enforce rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        self.last_request_time = time.time()

    @staticmethod
    def _parse_oanda_time(timestamp_str: str) -> datetime:
        """Parse OANDA ISO8601 timestamps with up to nanosecond precision.

        OANDA returns timestamps like '2025-09-15T14:14:27.714891445Z'.
        Python's datetime supports microseconds (max 6 digits). We truncate
        fractional seconds to 6 digits and preserve timezone info.
        """
        if not timestamp_str:
            return datetime.utcnow()
        ts = timestamp_str.replace('Z', '+00:00')
        # Split timezone
        match = re.match(r"^(.*?)(\.\d+)?([+-]\d{2}:?\d{2})$", ts)
        if match:
            base = match.group(1)
            frac = match.group(2) or ''
            tz = match.group(3)
            if frac:
                # Keep only 6 digits
                digits = re.sub(r"[^0-9]", "", frac)
                frac6 = digits[:6].ljust(6, '0')
                ts_clean = f"{base}.{frac6}{tz}"
            else:
                ts_clean = f"{base}{tz}"
            return datetime.fromisoformat(ts_clean)
        # Fallback: if no timezone part, append Z
        try:
            return datetime.fromisoformat(ts)
        except Exception:
            return datetime.utcnow()
    
    def _is_cloud_environment(self) -> bool:
        """Detect if running in Google Cloud environment"""
        return bool(
            os.getenv('GAE_ENV') or  # Google App Engine
            os.getenv('GAE_INSTANCE') or  # Google App Engine instance
            os.getenv('GOOGLE_CLOUD_PROJECT') or  # GCP project
            os.getenv('GAE_SERVICE')  # GAE service name
        )
    
    def _make_request(self, method: str, url: str, data: Optional[Dict] = None) -> Dict:
        """Make authenticated request to OANDA API with retries and DNS-safe handling"""
        self._rate_limit()
        attempts = int(os.getenv('OANDA_HTTP_RETRIES', '3'))
        backoff_base = float(os.getenv('OANDA_HTTP_BACKOFF', '0.5'))
        last_exc = None
        
        from urllib.parse import urlparse
        parsed = urlparse(url)
        host = parsed.hostname
        
        # CLOUD DEPLOYMENT FIX: Always use hostname, never substitute IP
        # Reason: IP substitution breaks SSL certificate validation (cert is for hostname, not IP)
        # Cloud environments: Platform handles DNS properly
        # Local environments: requests library handles DNS properly
        # 
        # Previous DNS pre-resolution code was causing issues:
        # 1. Picked DNS server IP (194.168.4.100) instead of resolved IPs
        # 2. Even with correct IP, SSL validation fails (certificate mismatch)
        # Solution: Use hostname directly, let requests/urllib handle DNS resolution
        
        if self._is_cloud_environment():
            logger.debug(f"☁️ Cloud environment: using hostname {host} (platform DNS)")
        else:
            logger.debug(f"💻 Local environment: using hostname {host} (standard DNS)")
        
        # Use standard headers (no IP substitution)
        headers_with_host = self.headers
        
        # Use standard requests (no custom adapter needed if we pre-resolved)
        session = requests
        
        try:
            for i in range(1, attempts + 1):
                try:
                    timeout = float(os.getenv('OANDA_HTTP_TIMEOUT', '8'))
                    if method.upper() == 'GET':
                        response = session.get(url, headers=headers_with_host, timeout=timeout)
                    elif method.upper() == 'POST':
                        response = session.post(url, headers=headers_with_host, json=data, timeout=timeout)
                    elif method.upper() == 'PUT':
                        response = session.put(url, headers=headers_with_host, json=data, timeout=timeout)
                    elif method.upper() == 'DELETE':
                        response = session.delete(url, headers=headers_with_host, timeout=timeout)
                    else:
                        raise ValueError(f"Unsupported HTTP method: {method}")
                    response.raise_for_status()
                    return response.json()
                except requests.exceptions.RequestException as e:
                    last_exc = e
                    # Log concise retry info; DNS/timeouts included here
                    logger.error(f"❌ OANDA request error (attempt {i}/{attempts}): {e}")
                    # No response body if DNS/timeout
                    if i < attempts:
                        time.sleep(backoff_base * i)
                    else:
                        break
        except Exception as e:
            last_exc = e
        # Exhausted retries
        if last_exc:
            if hasattr(last_exc, 'response') and getattr(last_exc, 'response') is not None:
                try:
                    logger.error(f"Response: {last_exc.response.text}")
                except Exception:
                    pass
            raise last_exc
        raise RuntimeError("Request failed but no exception was raised")
    
    def get_account_info(self) -> OandaAccount:
        """Get account information"""
        try:
            url = f"{self.accounts_endpoint}/{self.account_id}"
            response = self._make_request('GET', url)
            
            account_data = response['account']
            self.account_info = OandaAccount(
                account_id=account_data['id'],
                currency=account_data['currency'],
                balance=float(account_data['balance']),
                unrealized_pl=float(account_data.get('unrealizedPL', 0.0)),
                realized_pl=float(account_data.get('realizedPL', 0.0)),
                margin_used=float(account_data.get('marginUsed', 0.0)),
                margin_available=float(account_data.get('marginAvailable', 0.0)),
                open_trade_count=int(account_data.get('openTradeCount', 0)),
                open_position_count=int(account_data.get('openPositionCount', 0)),
                pending_order_count=int(account_data.get('pendingOrderCount', 0))
            )
            
            logger.info(f"✅ Account info retrieved - Balance: {self.account_info.balance} {self.account_info.currency}")
            return self.account_info
            
        except Exception as e:
            logger.error(f"❌ Failed to get account info: {e}")
            # Fallback: return last known account_info if present to avoid crashing callers
            if self.account_info is not None:
                logger.warning("⚠️ Returning cached account_info due to API failure")
                return self.account_info
            raise
    
    def get_current_price(self, instrument: str) -> OandaPrice:
        """Get current price for a single instrument"""
        prices = self.get_current_prices([instrument], force_refresh=True)
        return prices.get(instrument)
    
    def get_current_prices(self, instruments: List[str], force_refresh: bool = False) -> Dict[str, OandaPrice]:
        """Get current prices for instruments with optional cache bypass
        
        Args:
            instruments: List of instrument names (e.g., ['EUR_USD', 'GBP_USD'])
            force_refresh: If True, always fetch from API. If False, may return cached data.
        
        Returns:
            Dictionary mapping instrument name to OandaPrice object
        """
        try:
            # If force_refresh is False and we have cached prices, check if they're recent enough
            if not force_refresh and self.current_prices:
                # Check if cached prices are < 5 seconds old
                now = datetime.now()
                all_fresh = True
                for inst in instruments:
                    if inst in self.current_prices:
                        cached_price = self.current_prices[inst]
                        # Handle timezone-aware timestamps
                        if cached_price.timestamp.tzinfo is not None:
                            now = now.replace(tzinfo=cached_price.timestamp.tzinfo)
                        age = (now - cached_price.timestamp).total_seconds()
                        if age > 5:
                            all_fresh = False
                            break
                    else:
                        all_fresh = False
                        break
                
                if all_fresh:
                    logger.debug(f"📦 Returning cached prices (< 5s old) for {len(instruments)} instruments")
                    return {inst: self.current_prices[inst] for inst in instruments if inst in self.current_prices}
            
            # Make fresh API call
            logger.debug(f"🔄 Making fresh API call for {len(instruments)} instruments (force_refresh={force_refresh})")
            
            params = {
                'instruments': ','.join(instruments),
                'includeHomeConversions': 'false'
            }
            
            url = f"{self.pricing_endpoint}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
            response = self._make_request('GET', url)
            
            prices = {}
            for price_data in response['prices']:
                instrument = price_data['instrument']
                bid = float(price_data['bids'][0]['price'])
                ask = float(price_data['asks'][0]['price'])
                timestamp = self._parse_oanda_time(price_data['time'])
                
                price = OandaPrice(
                    instrument=instrument,
                    bid=bid,
                    ask=ask,
                    timestamp=timestamp,
                    spread=ask - bid,
                    is_live=True
                )
                
                prices[instrument] = price
                self.current_prices[instrument] = price
            
            logger.info(f"✅ Retrieved FRESH prices for {len(prices)} instruments from OANDA API")
            return prices
            
        except Exception as e:
            logger.error(f"❌ Failed to get current prices: {e}")
            # Fallback to cached prices if available
            if self.current_prices:
                fallback = {inst: self.current_prices[inst] for inst in instruments if inst in self.current_prices}
                if fallback:
                    logger.warning(f"⚠️ Returning cached prices for {len(fallback)} instruments due to API failure")
                    return fallback
            return {}

    def get_candles(self, instrument: str, granularity: str = 'M1', count: int = 50, price: str = 'BA') -> Dict[str, Any]:
        """Fetch recent candles for an instrument.

        - granularity: e.g., 'M1', 'M5', 'H1'
        - count: number of candles (max allowed by OANDA is typically 5000)
        - price: 'M' (mid), 'B' (bid), 'A' (ask), or a combination like 'BA'

        Returns raw JSON dict from OANDA. Caller can parse as needed.
        """
        try:
            params = {
                'granularity': granularity,
                'count': str(int(count)),
                'price': price
            }
            url = f"{self.instruments_endpoint}/{instrument}/candles?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
            response = self._make_request('GET', url)
            return response
        except Exception as e:
            logger.error(f"❌ Failed to get candles for {instrument}: {e}")
            raise
    
    def place_market_order(self, instrument: str, units: int, stop_loss: Optional[float] = None, 
                          take_profit: Optional[float] = None) -> OandaOrder:
        """Place a market order"""
        try:
            # Ensure instrument-precision-compliant prices for protective orders
            def _price_dp(inst: str) -> int:
                if inst.endswith('_JPY') or inst == 'USD_JPY':
                    return 3
                if inst == 'XAU_USD':
                    return 2
                return 5
            def _round_px(px: Optional[float], dp: int) -> Optional[float]:
                if px is None:
                    return None
                return float(f"{px:.{dp}f}")
            dp = _price_dp(instrument)
            stop_loss_rounded = _round_px(stop_loss, dp)
            take_profit_rounded = _round_px(take_profit, dp)

            order_data = {
                'order': {
                    'type': 'MARKET',
                    'instrument': instrument,
                    'units': str(units),
                    'timeInForce': 'IOC',  # Immediate or Cancel (less strict than FOK)
                    'positionFill': 'DEFAULT'
                }
            }
            
            # Add stop loss if provided
            if stop_loss_rounded:
                order_data['order']['stopLossOnFill'] = {
                    'price': str(stop_loss_rounded)
                }
            
            # Add take profit if provided
            if take_profit_rounded:
                order_data['order']['takeProfitOnFill'] = {
                    'price': str(take_profit_rounded)
                }
            
            response = self._make_request('POST', self.orders_endpoint, order_data)
            
            # OANDA may return different shapes; support both create and fill transactions
            order_create = response.get('orderCreateTransaction') or response.get('orderCancelTransaction')
            order_fill = response.get('orderFillTransaction')
            if not order_create and not order_fill:
                raise ValueError(f"Unexpected order response: {response}")

            # Choose base transaction for instrument/units/type
            base_txn = order_create or order_fill
            order_id = base_txn['id']
            instrument = base_txn.get('instrument') or order_fill.get('instrument')
            units_value = int(base_txn.get('units') or order_fill.get('units') or 0)
            side = 'buy' if units_value > 0 else 'sell'
            order_type = base_txn.get('type', 'MARKET')
            time_in_force = base_txn.get('timeInForce', 'FOK')
            create_time = self._parse_oanda_time(base_txn['time'])
            status = 'FILLED' if order_fill else base_txn.get('state', 'PENDING')
            fill_time = None
            if order_fill and 'time' in order_fill:
                fill_time = self._parse_oanda_time(order_fill['time'])

            order = OandaOrder(
                order_id=order_id,
                instrument=instrument,
                units=units_value,
                side=side,
                type=order_type,
                price=None,  # Market orders don't have fixed price here
                stop_loss=stop_loss,
                take_profit=take_profit,
                time_in_force=time_in_force,
                status=status,
                create_time=create_time,
                fill_time=fill_time
            )
            
            self.orders[order.order_id] = order
            logger.info(f"✅ Market order placed: {instrument} {units} units")
            return order
            
        except Exception as e:
            logger.error(f"❌ Failed to place market order: {e}")
            raise

    def create_order(self, instrument: str, units: int, side: str, order_type: str,
                     stop_loss: Optional[float] = None, take_profit: Optional[float] = None,
                     price: Optional[float] = None, time_in_force: str = 'FOK') -> OandaOrder:
        """Compatibility wrapper used by OrderManager.

        - order_type: 'MARKET'|'LIMIT'|'STOP'
        - side: 'BUY'|'SELL'
        - units sign will be adjusted automatically based on side.
        """
        try:
            side_upper = (side or '').upper()
            ot = (order_type or 'MARKET').upper()
            signed_units = abs(int(units)) if side_upper == 'BUY' else -abs(int(units))
            if ot == 'MARKET':
                return self.place_market_order(instrument, signed_units, stop_loss, take_profit)
            if ot == 'LIMIT':
                if price is None:
                    raise ValueError("LIMIT order requires price")
                return self.place_limit_order(instrument, signed_units, price, time_in_force, stop_loss, take_profit)
            if ot == 'STOP':
                if price is None:
                    raise ValueError("STOP order requires price")
                return self.place_stop_order(instrument, signed_units, price, time_in_force, stop_loss, take_profit)
            raise ValueError(f"Unsupported order type: {order_type}")
        except Exception as e:
            logger.error(f"❌ Failed to create order: {e}")
            raise
    
    def place_limit_order(self, instrument: str, units: int, price: float,
                          time_in_force: str = 'GTC',
                          stop_loss: Optional[float] = None,
                          take_profit: Optional[float] = None) -> OandaOrder:
        """Place a limit order.

        time_in_force options: GTC, GFD, GTT. Default GTC.
        """
        try:
            # Ensure instrument-precision-compliant prices
            def _price_dp(inst: str) -> int:
                if inst.endswith('_JPY') or inst == 'USD_JPY':
                    return 3
                if inst == 'XAU_USD':
                    return 2
                return 5

            def _round_px(px: Optional[float], dp: int) -> Optional[float]:
                if px is None:
                    return None
                return float(f"{px:.{dp}f}")

            dp = _price_dp(instrument)
            price = _round_px(price, dp)
            stop_loss = _round_px(stop_loss, dp)
            take_profit = _round_px(take_profit, dp)

            order_data = {
                'order': {
                    'type': 'LIMIT',
                    'instrument': instrument,
                    'units': str(units),
                    'price': str(price),
                    'timeInForce': time_in_force,
                    'positionFill': 'DEFAULT'
                }
            }

            if stop_loss:
                order_data['order']['stopLossOnFill'] = {
                    'price': str(stop_loss)
                }

            if take_profit:
                order_data['order']['takeProfitOnFill'] = {
                    'price': str(take_profit)
                }

            response = self._make_request('POST', self.orders_endpoint, order_data)

            order_create = response.get('orderCreateTransaction') or response.get('orderCancelTransaction')
            if not order_create:
                raise ValueError(f"Unexpected limit order response: {response}")

            order_id = order_create['id']
            order_type = order_create.get('type', 'LIMIT')
            time_in_force_resp = order_create.get('timeInForce', time_in_force)
            create_time = self._parse_oanda_time(order_create['time'])
            instrument_resp = order_create.get('instrument', instrument)
            units_value = int(order_create.get('units', str(units)))
            side = 'buy' if units_value > 0 else 'sell'

            order = OandaOrder(
                order_id=order_id,
                instrument=instrument_resp,
                units=units_value,
                side=side,
                type=order_type,
                price=price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                time_in_force=time_in_force_resp,
                status=order_create.get('state', 'PENDING'),
                create_time=create_time,
            )

            self.orders[order.order_id] = order
            logger.info(f"✅ Limit order placed: {instrument} {units} @ {price}")
            return order

        except Exception as e:
            logger.error(f"❌ Failed to place limit order: {e}")
            raise

    def place_stop_order(self, instrument: str, units: int, price: float,
                         time_in_force: str = 'GTC',
                         stop_loss: Optional[float] = None,
                         take_profit: Optional[float] = None) -> OandaOrder:
        """Place a stop order (stop market).

        Commonly used as a protective stop: for a long position, place a sell STOP below;
        for a short position, place a buy STOP above. Using netting, this will reduce/close.
        """
        try:
            order_data = {
                'order': {
                    'type': 'STOP',
                    'instrument': instrument,
                    'units': str(units),
                    'price': str(price),
                    'timeInForce': time_in_force,
                    'positionFill': 'DEFAULT'
                }
            }

            if stop_loss:
                order_data['order']['stopLossOnFill'] = {
                    'price': str(stop_loss)
                }

            if take_profit:
                order_data['order']['takeProfitOnFill'] = {
                    'price': str(take_profit)
                }

            response = self._make_request('POST', self.orders_endpoint, order_data)

            order_create = response.get('orderCreateTransaction') or response.get('orderCancelTransaction')
            if not order_create:
                raise ValueError(f"Unexpected stop order response: {response}")

            order_id = order_create['id']
            order_type = order_create.get('type', 'STOP')
            time_in_force_resp = order_create.get('timeInForce', time_in_force)
            create_time = self._parse_oanda_time(order_create['time'])
            instrument_resp = order_create.get('instrument', instrument)
            units_value = int(order_create.get('units', str(units)))
            side = 'buy' if units_value > 0 else 'sell'

            order = OandaOrder(
                order_id=order_id,
                instrument=instrument_resp,
                units=units_value,
                side=side,
                type=order_type,
                price=price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                time_in_force=time_in_force_resp,
                status=order_create.get('state', 'PENDING'),
                create_time=create_time,
            )

            self.orders[order.order_id] = order
            logger.info(f"✅ Stop order placed: {instrument} {units} @ {price}")
            return order

        except Exception as e:
            logger.error(f"❌ Failed to place stop order: {e}")
            raise
    
    def get_positions(self) -> Dict[str, OandaPosition]:
        """Get current positions"""
        try:
            response = self._make_request('GET', self.positions_endpoint)
            
            positions = {}
            for position_data in response['positions']:
                instrument = position_data['instrument']
                long_units = int(position_data['long']['units'])
                short_units = int(position_data['short']['units'])
                
                position = OandaPosition(
                    instrument=instrument,
                    long_units=long_units,
                    short_units=short_units,
                    long_unrealized_pl=float(position_data['long']['unrealizedPL']),
                    short_unrealized_pl=float(position_data['short']['unrealizedPL']),
                    long_margin_used=float(position_data['long'].get('marginUsed', 0.0)),
                    short_margin_used=float(position_data['short'].get('marginUsed', 0.0)),
                    long_avg_price=float(position_data['long'].get('averagePrice', 0.0)) if position_data['long'].get('averagePrice') else None,
                    short_avg_price=float(position_data['short'].get('averagePrice', 0.0)) if position_data['short'].get('averagePrice') else None,
                    unrealized_pl=float(position_data['unrealizedPL']),
                    margin_used=float(position_data.get('marginUsed', 0.0))
                )
                
                positions[instrument] = position
            
            self.positions = positions
            logger.info(f"✅ Retrieved {len(positions)} positions")
            return positions
            
        except Exception as e:
            logger.error(f"❌ Failed to get positions: {e}")
            raise
    
    # ---------- Trades and protective orders management ----------
    def get_open_trades(self) -> List[Dict[str, Any]]:
        """Return raw open trades list from OANDA.

        Shape (per trade) is an OANDA dict; we do not coerce here to preserve all fields
        such as stop loss / take profit order attachments.
        """
        try:
            url = f"{self.trades_endpoint}?state=OPEN"
            response = self._make_request('GET', url)
            trades = response.get('trades', [])
            logger.info(f"✅ Retrieved {len(trades)} open trades")
            return trades
        except Exception as e:
            logger.error(f"❌ Failed to get open trades: {e}")
            raise

    def update_trade_protective_orders(self, trade_id: str,
                                       stop_loss: Optional[float] = None,
                                       take_profit: Optional[float] = None) -> Dict[str, Any]:
        """Attach or replace SL/TP on an existing trade.

        Endpoint: PUT /v3/accounts/{accountID}/trades/{tradeSpecifier}/orders
        Docs: https://developer.oanda.com/rest-live-v20/trades-ep/
        """
        try:
            data: Dict[str, Any] = {}
            if stop_loss is not None:
                data['stopLoss'] = {
                    'timeInForce': 'GTC',
                    'price': str(stop_loss)
                }
            if take_profit is not None:
                data['takeProfit'] = {
                    'timeInForce': 'GTC',
                    'price': str(take_profit)
                }
            if not data:
                raise ValueError("At least one of stop_loss or take_profit must be provided")
            url = f"{self.trades_endpoint}/{trade_id}/orders"
            # OANDA expects a flat object with optional keys: takeProfit, stopLoss, trailingStopLoss
            response = self._make_request('PUT', url, data)
            logger.info(f"✅ Updated protective orders for trade {trade_id} (SL={stop_loss}, TP={take_profit})")
            return response
        except Exception as e:
            logger.error(f"❌ Failed to update protective orders for trade {trade_id}: {e}")
            raise

    def ensure_protective_stop_for_instrument(self, instrument: str,
                                              percent_sl: float = 0.005,
                                              prefer_side: Optional[str] = None) -> int:
        """Ensure all open trades for instrument have a Stop Loss.

        percent_sl: distance from current price as fraction (e.g., 0.005 = 0.5%).
        Returns number of trades updated.
        """
        try:
            prices = self.get_current_prices([instrument])
            px = prices[instrument]
            mid = (px.bid + px.ask) / 2.0
            trades = [t for t in self.get_open_trades() if t.get('instrument') == instrument]
            updated = 0
            for t in trades:
                units = float(t.get('currentUnits', 0))
                side = 'buy' if units > 0 else 'sell'
                if prefer_side and side != prefer_side:
                    continue
                # Determine current protective orders if any
                has_sl = bool(t.get('stopLossOrder') or t.get('stopLossOnFill'))
                # Compute SL price
                if side == 'buy':
                    sl_price = mid * (1.0 - percent_sl)
                else:
                    sl_price = mid * (1.0 + percent_sl)
                # Round according to instrument dp
                def _price_dp(inst: str) -> int:
                    if inst.endswith('_JPY') or inst == 'USD_JPY':
                        return 3
                    if inst == 'XAU_USD':
                        return 2
                    return 5
                dp = _price_dp(instrument)
                sl_price = float(f"{sl_price:.{dp}f}")
                if not has_sl:
                    self.update_trade_protective_orders(t['id'], stop_loss=sl_price)
                    updated += 1
            return updated
        except Exception as e:
            logger.error(f"❌ Failed to ensure protective stop for {instrument}: {e}")
            raise
    
    def close_trade(self, trade_id: str, units: Optional[int] = None) -> Dict:
        """Close a specific trade (full or partial)"""
        try:
            data = {}
            if units:
                data['units'] = str(units)  # Partial close
            else:
                data['units'] = 'ALL'  # Full close
            
            url = f"{self.trades_endpoint}/{trade_id}/close"
            response = self._make_request('PUT', url, data)
            
            logger.info(f"✅ Trade closed: {trade_id} ({units if units else 'ALL'} units)")
            return response
            
        except Exception as e:
            logger.error(f"❌ Failed to close trade {trade_id}: {e}")
            raise
    
    def close_position(self, instrument: str, long_units: Optional[int] = None, 
                      short_units: Optional[int] = None) -> Dict:
        """Close a position"""
        try:
            close_data = {
                'longUnits': str(long_units) if long_units else 'ALL',
                'shortUnits': str(short_units) if short_units else 'ALL'
            }
            
            url = f"{self.positions_endpoint}/{instrument}/close"
            response = self._make_request('PUT', url, close_data)
            
            logger.info(f"✅ Position closed: {instrument}")
            return response
            
        except Exception as e:
            logger.error(f"❌ Failed to close position: {e}")
            raise
    
    def is_connected(self) -> bool:
        """Check if OANDA connection is working"""
        try:
            self.get_account_info()
            return True
        except Exception as e:
            logger.error(f"❌ OANDA connection check failed: {e}")
            return False

# Global OANDA client instance (lazy initialization)
_oanda_client = None

def get_oanda_client() -> OandaClient:
    """Get the global OANDA client instance - FIXED: Uses unified credential loader"""
    global _oanda_client
    if _oanda_client is None:
        # Ensure credentials are loaded before creating client
        try:
            from .unified_credential_loader import ensure_credentials_loaded
            ensure_credentials_loaded()
        except Exception:
            pass  # Will try in OandaClient.__init__
        oanda_client = OandaClient()
    return oanda_client
