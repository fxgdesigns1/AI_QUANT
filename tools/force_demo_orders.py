#!/usr/bin/env python3
from src.core.settings import settings
"""
Force place small demo MARKET orders (paper) for each active strategy once.
- Places up to 1 small MARKET order per active strategy (demo accounts only).
- Respects the OANDA practice endpoint via env OANDA_BASE_URL and OANDA_API_KEY.
- Safe defaults: units=100 (very small). Only runs when OANDA_API_KEY present.
"""
import os
import yaml
import logging
import requests
from typing import Any, Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("force_demo_orders")

REPO_ROOT_CANDIDATES = [
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
    "/opt/quant_system_clean/google-cloud-trading-system",
]

def load_accounts_yaml() -> Dict[str, Any]:
    paths = [
        os.path.join(os.path.dirname(__file__), "..", "AI_QUANT_credentials", "accounts.yaml"),
        "/opt/quant_system_clean/google-cloud-trading-system/AI_QUANT_credentials/accounts.yaml",
    ]
    for p in paths:
        p = os.path.abspath(p)
        if os.path.exists(p):
            with open(p, "r") as fh:
                return yaml.safe_load(fh) or {}
    return {}

def normalize_signal(s):
    """Return a dict with keys expected by ai_trading.execute_trade"""
    try:
        if isinstance(s, dict):
            d = s
        else:
            # object with attributes
            d = {k: getattr(s, k) for k in ('instrument','side','entry_price','stop_loss','take_profit') if hasattr(s, k)}
        # ensure side is string
        if hasattr(d.get('side'), 'value'):
            d['side'] = d['side'].value
        if isinstance(d.get('side'), str):
            d['side'] = d['side']
        # set order_type and strategy
        d.setdefault('order_type', 'MARKET')
        d.setdefault('strategy', getattr(s, 'strategy', getattr(s, 'strategy_name', 'forced-demo')))
        return d
    except Exception as e:
        logger.warning("Could not normalize signal: %s", e)
        return {}

def place_market_order(account_id: str, token: str, instrument: str, units: int, tp: float, sl: float) -> Dict:
    base = os.getenv("OANDA_BASE_URL", "https://api-fxpractice.oanda.com")
    url = f"{base}/v3/accounts/{account_id}/orders"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    def round_price(inst: str, px: float) -> str:
        if inst in ('EUR_USD', 'GBP_USD', 'AUD_USD'):
            return f"{px:.5f}"
        if inst == 'USD_JPY':
            return f"{px:.3f}"
        if inst == 'XAU_USD':
            return f"{px:.2f}"
        return f"{px:.5f}"

    sl_str = round_price(instrument, sl)
    tp_str = round_price(instrument, tp)
    order_data = {
        "order": {
            "type": "MARKET",
            "instrument": instrument,
            "units": str(units),
            "timeInForce": "FOK",
            "positionFill": "DEFAULT",
            "stopLossOnFill": {"price": sl_str},
            "takeProfitOnFill": {"price": tp_str}
        }
    }
    r = requests.post(url, headers=headers, json=order_data, timeout=15)
    try:
        return {"status": r.status_code, "body": r.json()}
    except Exception:
        return {"status": r.status_code, "body": r.text}

def main():
    token = settings.oanda_api_key
    if not token:
        logger.error("OANDA_API_KEY missing in environment; aborting demo order placement.")
        return

    accounts_doc = load_accounts_yaml()
    accounts = accounts_doc.get("accounts", {}) if isinstance(accounts_doc, dict) else {}
    placed = []
    # Use dashboard market snapshot for price references
    try:
        dash = requests.get(os.getenv("DASHBOARD_URL","https://ai-quant-trading.uc.r.appspot.com/api/status"), timeout=10).json()
        market = dash.get("market_data", {})
    except Exception:
        market = {}

    for name, cfg in accounts.items():
        acct_id = cfg.get("account_id")
        strategy = cfg.get("strategy")
        if not acct_id or not strategy:
            continue
        # choose instrument to trade: first in trading_pairs or first in strategy default
        instrs = cfg.get("trading_pairs") or cfg.get("instruments") or []
        instrument = instrs[0] if instrs else "EUR_USD"
        # price reference
        md = market.get(instrument, {})
        ask = float(md.get("ask") or md.get("last") or 0.0)
        bid = float(md.get("bid") or ask)
        if ask == 0:
            logger.info("No price for %s; skipping %s", instrument, name)
            continue
        # small units (demo) - use conservative 100 units
        units = 100
        # compute simple tp/sl and round according to instrument precision
        sl = bid * 0.995
        tp = ask * 1.005
        def round_price(inst: str, px: float) -> float:
            if inst in ('EUR_USD', 'GBP_USD', 'AUD_USD'):
                return float(f"{px:.5f}")
            if inst == 'USD_JPY':
                return float(f"{px:.3f}")
            if inst == 'XAU_USD':
                return float(f"{px:.2f}")
            return float(f"{px:.5f}")
        sl = round_price(instrument, sl)
        tp = round_price(instrument, tp)
        logger.info("Placing demo MARKET for account %s (%s) %s %d units", acct_id, name, instrument, units)
        res = place_market_order(acct_id, token, instrument, units, tp, sl)
        placed.append({"account": name, "account_id": acct_id, "instrument": instrument, "units": units, "result": res})
        # limit to 1 order per account
    print({"placed": placed})

if __name__ == "__main__":
    main()


