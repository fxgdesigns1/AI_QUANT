# Strategy & Configuration Guide

This project now uses a unified strategy registry and account-driven configuration so every runtime component stays in sync. Use this checklist whenever you add or edit strategies.

---

## Key Files

- `Sync folder MAC TO PC/DESKTOP_HANDOFF_PACKAGE/google-cloud-trading-system/src/strategies/registry.py`
  - Authoritative list of strategies.
  - Provides canonical keys, display names, and factory helpers (`StrategyDefinition`).
  - Add new strategies here, and include any common synonyms in `_STRATEGY_SYNONYMS`.

- `Sync folder MAC TO PC/DESKTOP_HANDOFF_PACKAGE/google-cloud-trading-system/src/core/account_manager.py`
  - Loads account → strategy assignments.
  - Prefers `accounts.yaml` (auto-discovered under `AI_QUANT_credentials/` or `config/`); falls back to env vars.
  - Ensures each account shares canonical `strategy_id`, risk settings, instruments, and enabled flag.

- `Sync folder MAC TO PC/DESKTOP_HANDOFF_PACKAGE/google-cloud-trading-system/src/core/strategy_manager.py`
  - Builds live strategy instances directly from `AccountManager` configs.
  - Metrics/assignments stay keyed by the canonical strategy IDs from the registry.
  - Pause/resume controls call into this manager.

- `Sync folder MAC TO PC/DESKTOP_HANDOFF_PACKAGE/google-cloud-trading-system/src/dashboard/advanced_dashboard.py`
  - Hydrates dashboard state from the same account configs.
  - Uses per-account strategy instances for signal execution and status reporting.

- `Sync folder MAC TO PC/DESKTOP_HANDOFF_PACKAGE/google-cloud-trading-system/main.py`
  - `/actions/strategy` resolves requested targets with `StrategyManager`.
  - Confirmed actions invoke `pause_strategy` / `resume_strategy`; falls back to global pause if manager unavailable.

---

## Daily Workflow

1. **Update Strategy Logic**
   - Implement or edit code under `src/strategies/` (e.g. `alpha.py`, `gold_scalping.py`).
   - Register the strategy in `registry.py` with a canonical key and factory.

2. **Assign Strategy to Account**
   - Preferred: edit `AI_QUANT_credentials/accounts.yaml` (or whichever `accounts.yaml` is loaded).
     ```yaml
     accounts:
       primary:
         account_id: "101-004-..."
         strategy: "gold_scalping"  # canonical key or synonym
         active: true
         risk_settings:
           max_risk_per_trade: 0.02
           daily_trade_limit: 50
     ```
   - Optional fallback: update env vars in `AI_QUANT_credentials/oanda_config.env` (`PRIMARY_STRATEGY`, etc.).

3. **Restart Services**
   - Ensure the runtime re-reads configs (e.g. redeploy to GCP or restart the local service).

4. **Verify Dashboard**
   - `/api/status` should list `strategy_id` (canonical key) and `strategy_name` (display label) per account.
   - Strategy switcher commands (`/action strategy pause <target>`) should confirm specific targets.

---

## Adding a New Strategy (Example)

1. Create `src/strategies/new_strat.py` with `get_new_strat_strategy()` factory.
2. Register it:
   ```python
   STRATEGY_REGISTRY["new_strat"] = StrategyDefinition(
       key="new_strat",
       display_name="New Strat",
       factory=get_new_strat_strategy,
       description="...",
   )
   _STRATEGY_SYNONYMS["new"] = "new_strat"
   ```
3. Map an account in `accounts.yaml`:
   ```yaml
   my_new_lane:
     account_id: "101-..."
     strategy: "new_strat"
     active: true
   ```
4. Redeploy/restart. The dashboard and strategy manager auto-initialize the new lane.

---

## Strategy Switcher Commands

- Example payload (POST `/actions/strategy`):
  ```json
  { "action": "pause", "target": "PRIMARY_ultra_strict_forex" }
  ```
- Confirmation executes via `StrategyManager`. Response includes `targets` paused/resumed and any errors.

---

## Troubleshooting

- **Strategy Not Updating**
  - Ensure the canonical key exists in `registry.py` and the account’s `strategy` field references that key (or synonym).
  - Confirm the account `active: true` in YAML.
  - Restart the service so managers rebuild from fresh config.

- **Dashboard Shows Old Strategy Name**
  - The dashboard now reads `strategy_name` from the registry; check the registry entry and redeploy.

- **Switcher Says “no matching strategies”**
  - The command target must match a canonical strategy ID, strategy key, strategy name, or account name/ID; check `/api/status` for current IDs.

Keep this guide updated whenever the config flow changes. Cursor surfaces this file under the Gcloud system root—review it before editing strategies.











