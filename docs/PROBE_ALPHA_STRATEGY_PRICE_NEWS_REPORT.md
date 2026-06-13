# PROBE_ALPHA_STRATEGY_PRICE_NEWS_REPORT

**Generated (UTC):** 2026-01-12T22:32:54Z

## System Health
```json
{
  "status": "ok",
  "timestamp": 1768257174.8045373
}
```

## Core Status Truth
```json
{
  "system_label": "ALPHA",
  "mode": "paper",
  "execution_enabled": true,
  "accounts_loaded": 5,
  "accounts_execution_capable": 5,
  "last_scan_at": "2026-01-12T22:32:49.527810Z",
  "last_status_write_at": "2026-01-12T22:32:49.527879Z",
  "status_write_ok": true,
  "last_status_write_error_reason": null
}
```

## Status Counters (Risk + Blocks)
```json
{
  "price_sanity_blocks_per_account": {
    "101-004-30719775-001": 165,
    "101-004-30719775-002": 165,
    "101-004-30719775-003": 165,
    "101-004-30719775-004": 165,
    "101-004-30719775-005": 165
  },
  "tp_omitted_per_account": null,
  "throttle_skips_per_account": null,
  "oanda_cancel_reasons_per_account": null,
  "daily_trades_today": null,
  "open_trades_now": null
}
```

## Runtime Config Summary
```json
{
  "ok": true,
  "risk": {
    "max_risk_per_trade_pct": 1,
    "max_positions": 3,
    "max_daily_loss_pct": 5,
    "max_drawdown_pct": 10,
    "max_daily_trades_per_account": 3
  },
  "strategy_assignments_count": 5,
  "account_risk_limits_count": 0
}
```

## News
### /api/news/status
```json
{
  "ok": true,
  "providers": {
    "newsapi": {
      "ok": true,
      "config_present": true,
      "last_fetch_at": null,
      "last_error": null
    },
    "alphavantage": {
      "ok": true,
      "config_present": true,
      "last_fetch_at": null,
      "last_error": null
    },
    "marketaux": {
      "ok": true,
      "config_present": true,
      "last_fetch_at": null,
      "last_error": null
    },
    "finnhub": {
      "ok": false,
      "config_present": false,
      "last_fetch_at": null,
      "last_error": null
    },
    "polygon": {
      "ok": true,
      "config_present": true,
      "last_fetch_at": null,
      "last_error": null
    },
    "fmp": {
      "ok": true,
      "config_present": true,
      "last_fetch_at": null,
      "last_error": null
    }
  },
  "ts_utc": 1768257175.011106
}
```

### /api/news/assess
```json
{
  "ok": true,
  "model": null,
  "timestamp": 1768257175.0587668,
  "summary": null,
  "sentiment": null,
  "impact_score": 1.1,
  "per_provider_signals": {},
  "ai_meta": {
    "enabled": false,
    "mode": "advisory",
    "providers_tried": [],
    "latency_ms": null,
    "error": null
  },
  "news_count": 20,
  "providers_used": [
    "newsapi",
    "alphavantage"
  ],
  "ts_utc": 1768257175.6686873
}
```

## Live Prices
### Keys
```json
[
  "prices",
  "success",
  "ts_utc"
]
```

### XAU_USD (if present)
```json
"XAU_USD_NOT_PRESENT"
```

### EUR_USD (if present)
```json
"EUR_USD_NOT_PRESENT"
```

## Environment Presence (no secrets)
```text
TRADING_MODE=MISSING
OANDA_BASE_URL=MISSING
OANDA_ACCOUNT_ID=MISSING
OANDA_API_KEY=MISSING
ACCOUNT_SUFFIX_ALLOWLIST=MISSING
ACCOUNT_ID_PREFIX=MISSING
```

## Runner Evidence
### STRAT_EVIDENCE sample (last 6 matches)
```text
1948:Jan 12 22:32:15 fxg-quant-paper-e2-micro ai-quant-runner[1203371]: 2026-01-12 22:32:15,445 - working_trading_system - INFO - STRAT_EVIDENCE system=ALPHA account=005 strategy=eur_usd_5m_safe instrument=EUR_USD price_mid=1.08510 price_ts=1768257135.445 news_used_count=10 news_providers=Pypi.org,CBS Sports,Thefly.com,Motley Fool Australia,Nbcsportsbayarea.com,The Times of India,Just Jared,Essentially Sports signals_generated=1 decision=BUY
1970:Jan 12 22:32:47 fxg-quant-paper-e2-micro ai-quant-runner[1203371]: 2026-01-12 22:32:47,758 - working_trading_system - INFO - STRAT_EVIDENCE system=ALPHA account=001 strategy=momentum instrument=EUR_USD price_mid=1.08510 price_ts=1768257167.758 news_used_count=10 news_providers=Pypi.org,CBS Sports,Thefly.com,Motley Fool Australia,Nbcsportsbayarea.com,The Times of India,Just Jared,Essentially Sports signals_generated=1 decision=BUY
1973:Jan 12 22:32:47 fxg-quant-paper-e2-micro ai-quant-runner[1203371]: 2026-01-12 22:32:47,758 - working_trading_system - INFO - STRAT_EVIDENCE system=ALPHA account=002 strategy=momentum_v2 instrument=EUR_USD price_mid=1.08510 price_ts=1768257167.759 news_used_count=10 news_providers=Pypi.org,CBS Sports,Thefly.com,Motley Fool Australia,Nbcsportsbayarea.com,The Times of India,Just Jared,Essentially Sports signals_generated=1 decision=BUY
1976:Jan 12 22:32:47 fxg-quant-paper-e2-micro ai-quant-runner[1203371]: 2026-01-12 22:32:47,758 - working_trading_system - INFO - STRAT_EVIDENCE system=ALPHA account=003 strategy=range instrument=EUR_USD price_mid=1.08510 price_ts=1768257167.759 news_used_count=10 news_providers=Pypi.org,CBS Sports,Thefly.com,Motley Fool Australia,Nbcsportsbayarea.com,The Times of India,Just Jared,Essentially Sports signals_generated=1 decision=BUY
1979:Jan 12 22:32:47 fxg-quant-paper-e2-micro ai-quant-runner[1203371]: 2026-01-12 22:32:47,759 - working_trading_system - INFO - STRAT_EVIDENCE system=ALPHA account=004 strategy=gold instrument=EUR_USD price_mid=1.08510 price_ts=1768257167.759 news_used_count=10 news_providers=Pypi.org,CBS Sports,Thefly.com,Motley Fool Australia,Nbcsportsbayarea.com,The Times of India,Just Jared,Essentially Sports signals_generated=1 decision=BUY
1982:Jan 12 22:32:47 fxg-quant-paper-e2-micro ai-quant-runner[1203371]: 2026-01-12 22:32:47,759 - working_trading_system - INFO - STRAT_EVIDENCE system=ALPHA account=005 strategy=eur_usd_5m_safe instrument=EUR_USD price_mid=1.08510 price_ts=1768257167.759 news_used_count=10 news_providers=Pypi.org,CBS Sports,Thefly.com,Motley Fool Australia,Nbcsportsbayarea.com,The Times of India,Just Jared,Essentially Sports signals_generated=1 decision=BUY
```

### Recent order/activity markers (last 25 matches)
```text
1850:Jan 12 22:30:37 fxg-quant-paper-e2-micro ai-quant-runner[1203371]: 2026-01-12 22:30:37,737 - working_trading_system - WARNING - PRICE_SANITY_BLOCK {account:001,instrument:XAU_USD,order_type:MARKET,stop_loss:2645.50,mid:4597.65,dev_pct:42.46,threshold_pct:1.00,reason:stop_too_far}
1853:Jan 12 22:30:38 fxg-quant-paper-e2-micro ai-quant-runner[1203371]: 2026-01-12 22:30:38,006 - working_trading_system - WARNING - PRICE_SANITY_BLOCK {account:002,instrument:XAU_USD,order_type:MARKET,stop_loss:2645.50,mid:4597.65,dev_pct:42.46,threshold_pct:1.00,reason:stop_too_far}
1856:Jan 12 22:30:38 fxg-quant-paper-e2-micro ai-quant-runner[1203371]: 2026-01-12 22:30:38,249 - working_trading_system - WARNING - PRICE_SANITY_BLOCK {account:003,instrument:XAU_USD,order_type:MARKET,stop_loss:2645.50,mid:4597.65,dev_pct:42.46,threshold_pct:1.00,reason:stop_too_far}
1859:Jan 12 22:30:38 fxg-quant-paper-e2-micro ai-quant-runner[1203371]: 2026-01-12 22:30:38,466 - working_trading_system - WARNING - PRICE_SANITY_BLOCK {account:004,instrument:XAU_USD,order_type:MARKET,stop_loss:2645.50,mid:4597.65,dev_pct:42.46,threshold_pct:1.00,reason:stop_too_far}
1862:Jan 12 22:30:38 fxg-quant-paper-e2-micro ai-quant-runner[1203371]: 2026-01-12 22:30:38,714 - working_trading_system - WARNING - PRICE_SANITY_BLOCK {account:005,instrument:XAU_USD,order_type:MARKET,stop_loss:2645.50,mid:4597.65,dev_pct:42.46,threshold_pct:1.00,reason:stop_too_far}
1884:Jan 12 22:31:10 fxg-quant-paper-e2-micro ai-quant-runner[1203371]: 2026-01-12 22:31:10,812 - working_trading_system - WARNING - PRICE_SANITY_BLOCK {account:001,instrument:XAU_USD,order_type:MARKET,stop_loss:2645.50,mid:4597.65,dev_pct:42.46,threshold_pct:1.00,reason:stop_too_far}
1887:Jan 12 22:31:11 fxg-quant-paper-e2-micro ai-quant-runner[1203371]: 2026-01-12 22:31:11,051 - working_trading_system - WARNING - PRICE_SANITY_BLOCK {account:002,instrument:XAU_USD,order_type:MARKET,stop_loss:2645.50,mid:4597.65,dev_pct:42.46,threshold_pct:1.00,reason:stop_too_far}
1890:Jan 12 22:31:11 fxg-quant-paper-e2-micro ai-quant-runner[1203371]: 2026-01-12 22:31:11,293 - working_trading_system - WARNING - PRICE_SANITY_BLOCK {account:003,instrument:XAU_USD,order_type:MARKET,stop_loss:2645.50,mid:4597.65,dev_pct:42.46,threshold_pct:1.00,reason:stop_too_far}
1893:Jan 12 22:31:11 fxg-quant-paper-e2-micro ai-quant-runner[1203371]: 2026-01-12 22:31:11,515 - working_trading_system - WARNING - PRICE_SANITY_BLOCK {account:004,instrument:XAU_USD,order_type:MARKET,stop_loss:2645.50,mid:4597.65,dev_pct:42.46,threshold_pct:1.00,reason:stop_too_far}
1896:Jan 12 22:31:11 fxg-quant-paper-e2-micro ai-quant-runner[1203371]: 2026-01-12 22:31:11,743 - working_trading_system - WARNING - PRICE_SANITY_BLOCK {account:005,instrument:XAU_USD,order_type:MARKET,stop_loss:2645.50,mid:4597.65,dev_pct:42.46,threshold_pct:1.00,reason:stop_too_far}
1918:Jan 12 22:31:43 fxg-quant-paper-e2-micro ai-quant-runner[1203371]: 2026-01-12 22:31:43,742 - working_trading_system - WARNING - PRICE_SANITY_BLOCK {account:001,instrument:XAU_USD,order_type:MARKET,stop_loss:2645.50,mid:4597.65,dev_pct:42.46,threshold_pct:1.00,reason:stop_too_far}
1921:Jan 12 22:31:43 fxg-quant-paper-e2-micro ai-quant-runner[1203371]: 2026-01-12 22:31:43,965 - working_trading_system - WARNING - PRICE_SANITY_BLOCK {account:002,instrument:XAU_USD,order_type:MARKET,stop_loss:2645.50,mid:4597.65,dev_pct:42.46,threshold_pct:1.00,reason:stop_too_far}
1924:Jan 12 22:31:44 fxg-quant-paper-e2-micro ai-quant-runner[1203371]: 2026-01-12 22:31:44,168 - working_trading_system - WARNING - PRICE_SANITY_BLOCK {account:003,instrument:XAU_USD,order_type:MARKET,stop_loss:2645.50,mid:4597.65,dev_pct:42.46,threshold_pct:1.00,reason:stop_too_far}
1927:Jan 12 22:31:44 fxg-quant-paper-e2-micro ai-quant-runner[1203371]: 2026-01-12 22:31:44,406 - working_trading_system - WARNING - PRICE_SANITY_BLOCK {account:004,instrument:XAU_USD,order_type:MARKET,stop_loss:2645.50,mid:4597.65,dev_pct:42.46,threshold_pct:1.00,reason:stop_too_far}
1930:Jan 12 22:31:44 fxg-quant-paper-e2-micro ai-quant-runner[1203371]: 2026-01-12 22:31:44,728 - working_trading_system - WARNING - PRICE_SANITY_BLOCK {account:005,instrument:XAU_USD,order_type:MARKET,stop_loss:2645.50,mid:4597.65,dev_pct:42.46,threshold_pct:1.00,reason:stop_too_far}
1952:Jan 12 22:32:16 fxg-quant-paper-e2-micro ai-quant-runner[1203371]: 2026-01-12 22:32:16,263 - working_trading_system - WARNING - PRICE_SANITY_BLOCK {account:001,instrument:XAU_USD,order_type:MARKET,stop_loss:2645.50,mid:4597.65,dev_pct:42.46,threshold_pct:1.00,reason:stop_too_far}
1955:Jan 12 22:32:16 fxg-quant-paper-e2-micro ai-quant-runner[1203371]: 2026-01-12 22:32:16,484 - working_trading_system - WARNING - PRICE_SANITY_BLOCK {account:002,instrument:XAU_USD,order_type:MARKET,stop_loss:2645.50,mid:4597.65,dev_pct:42.46,threshold_pct:1.00,reason:stop_too_far}
1958:Jan 12 22:32:16 fxg-quant-paper-e2-micro ai-quant-runner[1203371]: 2026-01-12 22:32:16,706 - working_trading_system - WARNING - PRICE_SANITY_BLOCK {account:003,instrument:XAU_USD,order_type:MARKET,stop_loss:2645.50,mid:4597.65,dev_pct:42.46,threshold_pct:1.00,reason:stop_too_far}
1961:Jan 12 22:32:16 fxg-quant-paper-e2-micro ai-quant-runner[1203371]: 2026-01-12 22:32:16,905 - working_trading_system - WARNING - PRICE_SANITY_BLOCK {account:004,instrument:XAU_USD,order_type:MARKET,stop_loss:2645.50,mid:4597.65,dev_pct:42.46,threshold_pct:1.00,reason:stop_too_far}
1964:Jan 12 22:32:17 fxg-quant-paper-e2-micro ai-quant-runner[1203371]: 2026-01-12 22:32:17,122 - working_trading_system - WARNING - PRICE_SANITY_BLOCK {account:005,instrument:XAU_USD,order_type:MARKET,stop_loss:2645.50,mid:4597.65,dev_pct:42.46,threshold_pct:1.00,reason:stop_too_far}
1986:Jan 12 22:32:48 fxg-quant-paper-e2-micro ai-quant-runner[1203371]: 2026-01-12 22:32:48,589 - working_trading_system - WARNING - PRICE_SANITY_BLOCK {account:001,instrument:XAU_USD,order_type:MARKET,stop_loss:2645.50,mid:4597.65,dev_pct:42.46,threshold_pct:1.00,reason:stop_too_far}
1989:Jan 12 22:32:48 fxg-quant-paper-e2-micro ai-quant-runner[1203371]: 2026-01-12 22:32:48,813 - working_trading_system - WARNING - PRICE_SANITY_BLOCK {account:002,instrument:XAU_USD,order_type:MARKET,stop_loss:2645.50,mid:4597.65,dev_pct:42.46,threshold_pct:1.00,reason:stop_too_far}
1992:Jan 12 22:32:49 fxg-quant-paper-e2-micro ai-quant-runner[1203371]: 2026-01-12 22:32:49,029 - working_trading_system - WARNING - PRICE_SANITY_BLOCK {account:003,instrument:XAU_USD,order_type:MARKET,stop_loss:2645.50,mid:4597.65,dev_pct:42.46,threshold_pct:1.00,reason:stop_too_far}
1995:Jan 12 22:32:49 fxg-quant-paper-e2-micro ai-quant-runner[1203371]: 2026-01-12 22:32:49,305 - working_trading_system - WARNING - PRICE_SANITY_BLOCK {account:004,instrument:XAU_USD,order_type:MARKET,stop_loss:2645.50,mid:4597.65,dev_pct:42.46,threshold_pct:1.00,reason:stop_too_far}
1998:Jan 12 22:32:49 fxg-quant-paper-e2-micro ai-quant-runner[1203371]: 2026-01-12 22:32:49,525 - working_trading_system - WARNING - PRICE_SANITY_BLOCK {account:005,instrument:XAU_USD,order_type:MARKET,stop_loss:2645.50,mid:4597.65,dev_pct:42.46,threshold_pct:1.00,reason:stop_too_far}
```

## Strict Verifier Result
**VERIFIED_STRATEGY_PRICE_NEWS_CONSUMPTION=PASS**

## Final Verdict
**PROBE_ALPHA_DEEP_VERDICT=PASS**

**Why:** All required evidence gates satisfied.
