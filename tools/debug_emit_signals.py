#!/usr/bin/env python3
"""
Debug emitter - instantiate each registered strategy and attempt to generate
signals from current market data (read-only, no orders).
"""
import sys
import os
import requests
import yaml
import inspect
import json

# Ensure project path for imports on the VM
sys.path.insert(0, '/opt/quant_system_clean/google-cloud-trading-system')

from src.strategies.registry import resolve_strategy_key, create_strategy, available_strategies

DASH_URL = 'https://ai-quant-trading.uc.r.appspot.com/api/status'

def fetch_dashboard():
    r = requests.get(DASH_URL, timeout=10)
    r.raise_for_status()
    return r.json()

def load_accounts_yaml():
    path = '/opt/quant_system_clean/google-cloud-trading-system/AI_QUANT_credentials/accounts.yaml'
    try:
        with open(path, 'r', encoding='utf-8') as fh:
            data = yaml.safe_load(fh) or {}
        return data.get('accounts', {})
    except Exception:
        return {}

def safe_call_generate(strategy, market_data, account_cfg):
    signals = []
    try:
        if hasattr(strategy, 'generate_signals'):
            try:
                sig = strategy.generate_signals(market_data)
            except TypeError:
                sig = []
                instruments = account_cfg.get('trading_pairs') or getattr(strategy, 'instruments', None) or []
                if isinstance(instruments, list):
                    for inst in instruments:
                        md = market_data.get(inst)
                        try:
                            part = strategy.generate_signals(md, inst)
                            if part:
                                sig.extend(part)
                        except Exception:
                            pass
            signals = sig or []
        elif hasattr(strategy, 'analyze_market'):
            try:
                res = strategy.analyze_market(market_data)
                if isinstance(res, list):
                    signals = res
                elif hasattr(res, 'signals'):
                    signals = list(res.signals)
            except Exception:
                signals = []
    except Exception as e:
        print('Error calling strategy:', e)
        signals = []
    return signals

def wrap_market_data(raw_market):
    \"\"\"Convert raw dashboard market entries into objects strategies expect.\"\"\" 
    from types import SimpleNamespace
    from datetime import datetime
    import pandas as pd

    class MarketDataShim:
        def __init__(self, d):
            self._d = d or {}
            self.bid = self._d.get('bid')
            self.ask = self._d.get('ask')
            ts = self._d.get('timestamp')
            try:
                self.timestamp = datetime.fromisoformat(ts.replace('Z', '+00:00')) if ts else datetime.utcnow()
            except Exception:
                self.timestamp = datetime.utcnow()

        def to_dataframe(self):
            # Minimal single-row dataframe to satisfy strategies that call to_dataframe()
            return pd.DataFrame([{
                'timestamp': self.timestamp,
                'bid': self.bid,
                'ask': self.ask,
                'open': self._d.get('open'),
                'high': self._d.get('high'),
                'low': self._d.get('low'),
                'close': self._d.get('close'),
            }])

        def __getitem__(self, key):
            return self._d.get(key)

        def get(self, key, default=None):
            return self._d.get(key, default)

        def __repr__(self):
            return f\"MarketDataShim(bid={self.bid},ask={self.ask})\"

    wrapped = {}
    for k, v in (raw_market or {}).items():
        if isinstance(v, dict):
            wrapped[k] = MarketDataShim(v)
        else:
            wrapped[k] = v
    return wrapped

def summarize_and_print(signals):
    out = []
    for s in signals:
        try:
            if isinstance(s, dict):
                out.append(s)
                continue
            d = {}
            for attr in ('instrument','side','entry_price','take_profit','stop_loss','confidence','strength'):
                if hasattr(s, attr):
                    v = getattr(s, attr)
                    try:
                        if hasattr(v, 'value'):
                            v = v.value
                    except Exception:
                        pass
                    d[attr] = v
            out.append(d)
        except Exception:
            out.append(str(s))
    print(json.dumps(out, default=str, indent=2))

def main():
    print('Fetching dashboard...')
    status = fetch_dashboard()
    raw_market = status.get('market_data', {})
    market_data = wrap_market_data(raw_market)
    accounts = load_accounts_yaml()

    print(f'Loaded {len(accounts)} accounts from YAML')
    for acct_name, acct_cfg in accounts.items():
        raw = acct_cfg.get('strategy')
        resolved = resolve_strategy_key(raw)
        if not resolved:
            print('Could not resolve', raw)
            continue
        try:
            strat = create_strategy(resolved)
            print('\\n===', acct_name, '->', resolved, '===') 
            signals = safe_call_generate(strat, market_data, acct_cfg)
            print('Signals found:', len(signals))
            summarize_and_print(signals[:5])
        except Exception as e:
            print('Error instantiating', resolved, e)

    print('\\n-- Registry sample check --') 
    for defn in available_strategies():
        try:
            strat = defn.create()
            if not strat:
                continue
            print('\\n### Registry:', defn.key)
            signals = safe_call_generate(strat, market_data, {})
            print('Signals found:', len(signals))
            summarize_and_print(signals[:3])
        except Exception as e:
            print('Registry instantiate error:', defn.key, e)

    print('\\nDebug emitter finished.')

if __name__ == '__main__':
    main()


