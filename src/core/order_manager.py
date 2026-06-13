"""
Order Manager - Real OANDA Practice/Live order execution.

CONTRACT: All orders go to OANDA (Practice for paper, Live for live).
No mocks, no simulation. Paper mode uses OANDA Practice API (real orders).
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List

from src.core.settings import settings
try:
    from src.observability.structured_logger import logger
except ImportError:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

try:
    from src.observability.forensic_recorder import recorder
except ImportError:
    recorder = None

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    import urllib.request
    import urllib.parse


class OrderManager:
    """Real OANDA order manager - places actual orders via OANDA API"""
    
    def __init__(self):
        # Canonical OANDA configuration must come from settings (single source of truth)
        self.oanda_api_key = settings.oanda_api_key or ""
        self.oanda_env = settings.oanda_env

        # Derive base URL from env (practice|live) instead of ad‑hoc env vars
        oanda_base_url = os.getenv("OANDA_BASE_URL", "").strip()
        if oanda_base_url:
            self.oanda_base_url = oanda_base_url
        else:
            if self.oanda_env == "live":
                self.oanda_base_url = "https://api-fxtrade.oanda.com"
            else:
                self.oanda_base_url = "https://api-fxpractice.oanda.com"
        
        # Account prefix also comes from centralized settings
        self.account_id_prefix = settings.account_id_prefix
    
    def _get_headers(self) -> Dict[str, str]:
        """Get OANDA API headers"""
        return {
            "Authorization": f"Bearer {self.oanda_api_key}",
            "Content-Type": "application/json"
        }
    
    def _build_account_id(self, account_suffix: str) -> str:
        """Build full account ID from prefix + suffix"""
        return f"{self.account_id_prefix}{account_suffix}"
    
    def _mask_account_id(self, account_id: str) -> str:
        """Mask account ID for logging (show only last 3 chars)"""
        if len(account_id) > 6:
            return f"{account_id[:3]}***{account_id[-3:]}"
        return "***"
    
    def place_order(
        self,
        account_suffix: str,
        instrument: str,
        units: int,
        order_type: str = "MARKET",
        stop_loss_price: Optional[float] = None,
        take_profit_price: Optional[float] = None,
        time_in_force: str = "FOK"
    ) -> Dict[str, Any]:
        """
        Place a real OANDA order.
        """
        if not self.oanda_api_key:
            raise RuntimeError("OANDA_API_KEY not configured")
        
        account_id = self._build_account_id(account_suffix)
        account_id_masked = self._mask_account_id(account_id)
        
        # Build order payload
        order_payload = {
            "order": {
                "type": order_type,
                "instrument": instrument,
                "units": str(units),
                "timeInForce": time_in_force,
                "positionFill": "DEFAULT"
            }
        }
        
        # Add stop loss if provided
        if stop_loss_price is not None:
            order_payload["order"]["stopLossOnFill"] = {"price": f"{stop_loss_price:.5f}"}
        
        # Add take profit if provided
        if take_profit_price is not None:
            order_payload["order"]["takeProfitOnFill"] = {"price": f"{take_profit_price:.5f}"}
        
        # For XAU, adjust precision
        if "XAU" in instrument:
            if stop_loss_price is not None:
                order_payload["order"]["stopLossOnFill"]["price"] = f"{stop_loss_price:.2f}"
            if take_profit_price is not None:
                order_payload["order"]["takeProfitOnFill"]["price"] = f"{take_profit_price:.2f}"
        
        url = f"{self.oanda_base_url}/v3/accounts/{account_id}/orders"
        headers = self._get_headers()
        
        try:
            http_status = None
            if HAS_REQUESTS:
                response = requests.post(url, headers=headers, json=order_payload, timeout=20)
                http_status = response.status_code
                if http_status not in (200, 201):
                    error_text = response.text[:500]
                    raise RuntimeError(f"OANDA order failed: {http_status} - {error_text}")
                result = response.json()
            else:
                # Fallback to urllib if requests not available
                data = json.dumps(order_payload).encode('utf-8')
                req = urllib.request.Request(url, data=data, headers=headers, method='POST')
                with urllib.request.urlopen(req, timeout=20) as r:
                    http_status = r.status
                    if http_status not in (200, 201):
                        error_text = r.read().decode()[:500]
                        raise RuntimeError(f"OANDA order failed: {http_status} - {error_text}")
                    result = json.loads(r.read().decode())
            
            # Extract transaction IDs - ENFORCE: at least one tx id must exist
            order_create_tx = result.get("orderCreateTransaction", {})
            order_fill_tx = result.get("orderFillTransaction", {})
            order_cancel_tx = result.get("orderCancelTransaction", {})
            
            order_create_tx_id = order_create_tx.get("id") if order_create_tx else None
            order_fill_tx_id = order_fill_tx.get("id") if order_fill_tx else None
            order_cancel_tx_id = order_cancel_tx.get("id") if order_cancel_tx else None
            
            # BRUTAL TRUTH: If no transaction IDs, this is NOT a successful order
            if not (order_create_tx_id or order_fill_tx_id or order_cancel_tx_id):
                error_msg = f"OANDA response missing transaction IDs. Response keys: {list(result.keys())}"
                logger.error(f"❌ Order placement failed for account suffix {account_suffix}: {error_msg}")
                raise RuntimeError(f"OANDA order response invalid: {error_msg}")
            
            # Log with tx ids (safe fields only)
            tx_ids_str = f"orderCreateTransaction.id={order_create_tx_id}" if order_create_tx_id else ""
            if order_fill_tx_id:
                tx_ids_str += f", orderFillTransaction.id={order_fill_tx_id}"
            if order_cancel_tx_id:
                tx_ids_str += f", orderCancelTransaction.id={order_cancel_tx_id}"
            
            if hasattr(logger, "info"):
                logger.info(f"✅ Order placed on account suffix {account_suffix}: {tx_ids_str}")

            # FORENSIC: Record ENTRY trade event
            if recorder and order_fill_tx:
                trade_event = {
                    "event_type": "ENTRY",
                    "account": account_id,
                    "trade_id": order_fill_tx.get("tradeOpened", {}).get("tradeID") or order_fill_tx.get("id"),
                    "symbol": instrument,
                    "side": "BUY" if units > 0 else "SELL",
                    "units": abs(units),
                    "entry_price": float(order_fill_tx.get("price", 0)),
                    "stop_loss": stop_loss_price,
                    "take_profit": take_profit_price,
                    "transaction_id": order_fill_tx_id
                }
                recorder.record_trade_event(trade_event)
            
            return {
                "ok": True,
                "account_suffix": account_suffix,
                "account_id": account_id,
                "account_id_masked": account_id_masked,
                "instrument": instrument,
                "units": units,
                "oanda_status": http_status or 200,
                "tx_ids": {
                    "create_id": order_create_tx_id,
                    "fill_id": order_fill_tx_id,
                    "cancel_id": order_cancel_tx_id,
                },
                "orderCreateTransactionId": order_create_tx_id,
                "orderFillTransactionId": order_fill_tx_id,
                "raw_response_subset": {
                    "orderCreateTransaction": {
                        "id": order_create_tx_id,
                        "type": order_create_tx.get("type"),
                    } if order_create_tx else None,
                    "orderFillTransaction": {
                        "id": order_fill_tx_id,
                        "type": order_fill_tx.get("type"),
                    } if order_fill_tx else None,
                }
            }
        except Exception as e:
            error_msg = str(e)[:200]
            if hasattr(logger, "error"):
                logger.error(f"❌ Order placement failed for account suffix {account_suffix}: {error_msg}")
            raise RuntimeError(f"Order placement failed: {error_msg}")
    
    def get_open_trades(self, account_suffix: str) -> List[Dict[str, Any]]:
        """
        Get open trades for an account.
        
        Returns:
            List of trade dicts from OANDA openTrades endpoint
        """
        if not self.oanda_api_key:
            raise RuntimeError("OANDA_API_KEY not configured")
        
        account_id = self._build_account_id(account_suffix)
        url = f"{self.oanda_base_url}/v3/accounts/{account_id}/openTrades"
        headers = self._get_headers()
        
        try:
            if HAS_REQUESTS:
                response = requests.get(url, headers=headers, timeout=20)
                if response.status_code != 200:
                    error_text = response.text[:500]
                    raise RuntimeError(f"OANDA openTrades failed: {response.status_code} - {error_text}")
                result = response.json()
            else:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=20) as r:
                    if r.status != 200:
                        error_text = r.read().decode()[:500]
                        raise RuntimeError(f"OANDA openTrades failed: {r.status} - {error_text}")
                    result = json.loads(r.read().decode())
            
            return result.get("trades", [])
        except Exception as e:
            error_msg = str(e)[:200]
            if hasattr(logger, "error"):
                logger.error(f"❌ Failed to get open trades for account suffix {account_suffix}: {error_msg}")
            raise RuntimeError(f"Failed to get open trades: {error_msg}")
    
    def close_all_open_trades(self, account_suffix: str) -> Dict[str, Any]:
        """
        Close all open trades for an account.
        
        Returns:
            Dict with ok, account_suffix, affected_trade_ids, errors
        """
        if not self.oanda_api_key:
            raise RuntimeError("OANDA_API_KEY not configured")
        
        account_id = self._build_account_id(account_suffix)
        account_id_masked = self._mask_account_id(account_id)
        
        # Get open trades
        try:
            open_trades = self.get_open_trades(account_suffix)
        except Exception as e:
            return {
                "ok": False,
                "account_suffix": account_suffix,
                "account_id_masked": account_id_masked,
                "affected_trade_ids": [],
                "error": f"Failed to get open trades: {str(e)[:200]}"
            }
        
        if not open_trades:
            return {
                "ok": True,
                "account_suffix": account_suffix,
                "account_id_masked": account_id_masked,
                "affected_trade_ids": [],
                "message": "No open trades to close"
            }
        
        # Close each trade
        affected_trade_ids = []
        errors = []
        
        for trade in open_trades:
            trade_id = trade.get("id")
            if not trade_id:
                continue
            
            url = f"{self.oanda_base_url}/v3/accounts/{account_id}/trades/{trade_id}/close"
            headers = self._get_headers()
            
            try:
                if HAS_REQUESTS:
                    response = requests.put(url, headers=headers, timeout=20)
                    if response.status_code not in (200, 201):
                        error_text = response.text[:500]
                        errors.append(f"Trade {trade_id}: {response.status_code} - {error_text[:100]}")
                        continue
                    result = response.json()
                else:
                    req = urllib.request.Request(url, headers=headers, method='PUT')
                    with urllib.request.urlopen(req, timeout=20) as r:
                        if r.status not in (200, 201):
                            error_text = r.read().decode()[:500]
                            errors.append(f"Trade {trade_id}: {r.status} - {error_text[:100]}")
                            continue
                        result = json.loads(r.read().decode())
                
                affected_trade_ids.append(trade_id)
                if hasattr(logger, "info"):
                    logger.info(f"✅ Closed trade {trade_id} on account suffix {account_suffix}")

                # FORENSIC: Record EXIT trade event (PNL confirmation)
                order_fill = result.get("orderFillTransaction")
                if recorder and order_fill:
                    trade_event = {
                        "event_type": "EXIT",
                        "account": account_id,
                        "trade_id": trade_id,
                        "symbol": order_fill.get("instrument", "UNKNOWN"),
                        "side": "SELL" if float(order_fill.get("units", 0)) < 0 else "BUY", # Exit side is opposite of entry
                        "units": abs(float(order_fill.get("units", 0))),
                        "exit_price": float(order_fill.get("price", 0)),
                        "realised_pnl": float(order_fill.get("pl", 0)),
                        "transaction_id": order_fill.get("id")
                    }
                    recorder.record_trade_event(trade_event)

            except Exception as e:
                error_msg = str(e)[:200]
                errors.append(f"Trade {trade_id}: {error_msg}")
                if hasattr(logger, "error"):
                    logger.error(f"❌ Failed to close trade {trade_id}: {error_msg}")
        
        return {
            "ok": len(errors) == 0,
            "account_suffix": account_suffix,
            "account_id_masked": account_id_masked,
            "affected_trade_ids": affected_trade_ids,
            "errors": errors if errors else None
        }
    
    def get_open_orders(self):
        """Return empty orders (legacy compatibility)"""
        return []
