import os
import yaml
from google.cloud import firestore

# Configuration Paths
# We will use the file we just established as the 'Truth' on the VM
LOCAL_CONFIG_PATH = "trade_with_pat_orb_dual_session.yaml" 

# Firestore Configuration
PROJECT_ID = "ai-quant-trading"
COLLECTION_NAME = "strategies"
DOCUMENT_ID = "trade_with_pat_orb_dual"

def load_local_yaml(path):
    print(f"Reading local configuration from {path}...")
    with open(path, 'r') as file:
        return yaml.safe_load(file)

def upload_to_firestore(data):
    print(f"Connecting to Firestore project: {PROJECT_ID}...")
    db = firestore.Client(project=PROJECT_ID)
    
    doc_ref = db.collection(COLLECTION_NAME).document(DOCUMENT_ID)
    
    print(f"Uploading configuration to {COLLECTION_NAME}/{DOCUMENT_ID}...")
    # We upload the entire YAML structure as a document
    doc_ref.set(data)
    print("✅ Upload successful! The Cloud Truth is established.")

if __name__ == "__main__":
    # We need to recreate the content of the config file locally first since we deleted the temp one
    # This ensures we are uploading exactly what is running on the VM
    
    config_content = """
# =============================================================================
# TRADE WITH PAT - OPEN RANGE BREAKOUT (DUAL SESSION TEMPLATE)
# =============================================================================
global:
  timezone: "Europe/London"
  data_mode: "live_only"
  account_isolation: true
  paper_trading_only: true
  session_blackout:
    - "22:00-08:00"
  news_sources:
    primary: "marketaux"
    secondary: "oanda"
  telemetry:
    telegram_alerts: true
    telegram_token: os.getenv("TELEGRAM_BOT_TOKEN") or "REDACTED - use TELEGRAM_BOT_TOKEN environment variable"
    telegram_chat_id: "6100678501"
    log_level: "INFO"

strategies:
  trade_with_pat_orb_dual:
    name: "Trade With Pat ORB (London & NY)"
    strategy_type: "open_range_breakout_supply_demand"
    active: true
    instruments:
      london_lane:
        - "GBP_USD"
        - "EUR_USD"
        - "XAU_USD"
      ny_lane:
        - "EUR_USD"
        - "US500_USD"
        - "NAS100_USD"
        - "XAU_USD"
    parameters:
      range_window_minutes: 15
      breakout_timeframes: ["M5", "M1"]
      supply_demand_detection:
        entry_mode: "limit_on_return"
        min_candles: 3
        max_candles: 6
        reference_body_ratio: 0.6
        mitigation_buffer_pips: 2.0
        invalidate_if_range_retests: true
        auto_remap_on_extreme_break: true
      ema_filter:
        enabled: true
        period: 200
        timeframe: "M5"
        direction_bias: "session_trend"
      momentum_filter:
        enabled: true
        ema_stack: [3, 8, 21]
        confirmation_required: 2
        min_rsi: 55
        max_rsi: 45
        volume_surge_threshold: 1.2
      atr_filter:
        enabled: true
        period: 14
        min_atr_multiple: 0.35
        max_atr_multiple: 1.20
      news_filter:
        enabled: true
        high_impact_only: true
        lookback_minutes: 30
        cooldown_minutes: 30
        cancel_pending_orders: true
      session_templates:
        london_open:
          label: "London ORB"
          window: "08:00-08:15"
          timezone: "Europe/London"
          min_volume_score: 0.60
          min_range_pips: 8
          max_range_pips: 25
          per_session_trade_cap: 3
          killzone: "london_open"
        ny_open:
          label: "New York ORB"
          window: "14:30-14:45"
          timezone: "Europe/London"
          min_volume_score: 0.70
          min_range_pips: 10
          max_range_pips: 35
          per_session_trade_cap: 4
          killzone: "ny_overlap"
      target_logic:
        tp_multiple_of_range: 0.80
        tp_fallback_atr_multiple: 1.20
        partial_take_percentages: [0.6, 0.4]
        partial_take_levels: [0.6, 1.0]
        breakeven_trigger_pct_of_tp: 0.60
        trail_after_midline_retag: true
        hard_stop_buffer_pips: 2.5
      risk_overrides:
        max_risk_per_trade: 0.02
        min_risk_per_trade: 0.005
        max_total_exposure: 0.10
        max_positions: 5
        per_session_position_cap: 3
        max_trades_per_day: 12
        scale_in_on_retests: true
        scale_in_limit: 2
        auto_reduce_size_after_losses: true
        loss_reduction_factor: 0.5
      data_sources:
        - "oanda_live_prices"
        - "marketaux_news"
        - "oanda_position_ratio"
    metrics_targets:
      win_rate: 0.74
      avg_rr: 1.50
      monthly_return_target_pct: 5.0
      max_drawdown_pct: 4.0
      expected_trades_per_month: 40
      verification_windows_days: 2

accounts:
  - id: "orb_london_lane"
    name: "ORB London Session"
    strategy: "trade_with_pat_orb_dual"
    active: true
    description: "Lane A for AB testing — London open ORB scalps (demo only)."
    instruments: ["GBP_USD", "EUR_USD", "XAU_USD"]
    risk_settings:
      base_position_risk: 0.015
      max_positions: 3
      max_daily_loss_pct: 0.05
      enable_scale_up_to_portfolio_cap: true
      trade_window: "07:45-11:00"
      session_template: "london_open"
      alert_channel: "telegram"
  - id: "orb_newyork_lane"
    name: "ORB New York Session"
    strategy: "trade_with_pat_orb_dual"
    active: true
    description: "Lane B for AB testing — NYSE open ORB scalps (demo only)."
    instruments: ["EUR_USD", "US500_USD", "NAS100_USD", "XAU_USD"]
    risk_settings:
      base_position_risk: 0.02
      max_positions: 2
      max_daily_loss_pct: 0.05
      enable_scale_up_to_portfolio_cap: true
      trade_window: "14:15-18:00"
      session_template: "ny_open"
      alert_channel: "telegram"

risk_management:
  total_portfolio_exposure_cap: 0.10
  max_concurrent_positions: 5
  max_trades_per_day_total: 12
  max_scalps_per_session: 4
  kill_switch_drawdown_pct: 0.07
  kill_switch_consecutive_losses: 4
  hard_stop_trading_after_time: "18:30"
  scale_up_if_exposure_below_pct: 0.08
  automation_mode: "paper"
  execution_accounts: "demo_only"

trading_rules:
  enforce_live_data_only: true
  news_integration: true
  quality_filtering: true
  same_day_preference: true
  avoid_reentry_if_midline_broken: true
  pair_priority: ["EUR_USD", "GBP_USD", "XAU_USD", "US500_USD", "NAS100_USD"]
  telemetry_tags: ["ORB", "Scalping", "DualSession"]
  killzones: ["london_open", "london_ny_overlap", "ny_afternoon"]

performance_targets:
  min_win_rate: 0.70
  min_sharpe_ratio: 2.0
  min_monthly_return: 5.0
  max_drawdown: 5.0
  target_annual_return: 60.0
  backtest_reference:
    myfxbook_win_rate: 0.7438
    tradzella_win_rate: 0.8438
    equity_curve_gain_pct: 74.0
    compounding_enabled: true

monitoring:
  enable_logging: true
  save_trades: true
  performance_tracking: true
  alert_on_losses: true
  alert_threshold: 3
  track_per_pair: true
  dashboards:
    include_ab_lane_labels: true
    show_news_sentiment: true
"""
    
    # Save temp file
    with open(LOCAL_CONFIG_PATH, "w") as f:
        f.write(config_content)

    try:
        data = load_local_yaml(LOCAL_CONFIG_PATH)
        upload_to_firestore(data)
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if os.path.exists(LOCAL_CONFIG_PATH):
            os.remove(LOCAL_CONFIG_PATH)
            print("Cleaned up local temp file.")

